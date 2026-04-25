from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from time import sleep
from urllib.parse import urljoin, urlparse

import httpx
from linkfile_core.index import FileRecord
from linkfile_core.models import ShareDeliveryMode, StorageType, UploadResult
from linkfile_core.utils import (
    duration_seconds,
    expires_at_from_duration,
    guess_mime_type,
    sha256_file,
)

_NETWORK_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.NetworkError,
    httpx.PoolTimeout,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.WriteError,
    httpx.WriteTimeout,
)


class CloudreveStrategy:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.site_url = config["base_url"].rstrip("/")
        self.base_url = self._api_base_url(config["base_url"])
        self._access_token: str | None = config.get("access_token") or config.get("token")
        self._refresh_token: str | None = config.get("refresh_token")

    def test_connection(self) -> None:
        self._request(
            "GET",
            "/file",
            params={
                "uri": self._cloudreve_uri(self.config.get("root_path") or "/"),
                "page": 0,
                "page_size": 1,
            },
        )

    def upload_file(self, path: Path, *, expire: str | None = None) -> UploadResult:
        storage_key = self._remote_file_uri(path)
        upload_session = self._create_upload_session(path, storage_key)
        self._upload_content(path, upload_session)
        link = self._create_link(storage_key, expire=expire)
        prefer_direct_url = bool(self.config.get("prefer_direct_url"))
        return UploadResult(
            file_id=f"file_{uuid.uuid4().hex}",
            name=path.name,
            size=path.stat().st_size,
            mime_type=guess_mime_type(path),
            storage_method_id=self.config["id"],
            storage_type=StorageType.CLOUDREVE,
            storage_key=storage_key,
            share_url=None if prefer_direct_url else link,
            raw_url=link if prefer_direct_url else None,
            expires_at=expires_at_from_duration(expire),
            metadata={
                "sha256": sha256_file(path),
                "delivery_mode": (
                    ShareDeliveryMode.CLOUDREVE_DIRECT_URL
                    if prefer_direct_url
                    else ShareDeliveryMode.CLOUDREVE_SHARE_URL
                ),
            },
        )

    def download_file(self, record: FileRecord, destination: Path) -> Path:
        target = (
            destination / record.name
            if destination.exists() and destination.is_dir()
            else destination
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        download_url = self._download_url(record.storage_key)
        headers = self._auth_headers()
        with httpx.Client(timeout=60) as client:
            response = self._send_with_retries(
                lambda: client.get(download_url, headers=headers),
                "download file content",
            )
        response.raise_for_status()
        target.write_bytes(response.content)
        return target

    def delete_file(self, record: FileRecord) -> None:
        self._request(
            "DELETE",
            "/file",
            json={
                "uris": [self._cloudreve_uri(record.storage_key)],
                "unlink": False,
                "trash_bin": False,
            },
        )

    def generate_temporary_url(
        self,
        record: FileRecord,
        *,
        expire: str | None = None,
    ) -> str | None:
        if record.share_url and not self.config.get("prefer_direct_url"):
            return record.share_url
        return self._create_link(record.storage_key, expire=expire)

    def _create_upload_session(self, path: Path, storage_key: str) -> dict:
        parent_uri = storage_key.rsplit("/", 1)[0] or "/"
        directory = self._request(
            "GET",
            "/file",
            params={
                "uri": self._cloudreve_uri(parent_uri),
                "page": 0,
                "page_size": 1,
                "order_by": "name",
                "order": "asc",
            },
        )
        policy = directory.get("storage_policy") or {}
        policy_id = policy.get("id")
        if policy_id is None:
            raise RuntimeError("Cloudreve directory response did not include a storage policy.")

        upload_session = self._request(
            "PUT",
            "/file/upload",
            json={
                "uri": self._cloudreve_uri(storage_key),
                "size": path.stat().st_size,
                "last_modified": int(path.stat().st_mtime * 1000),
                "policy_id": policy_id,
                "mime_type": guess_mime_type(path),
            },
        )
        if not isinstance(upload_session, dict):
            raise RuntimeError("Cloudreve upload session response was not an object.")
        upload_session.setdefault("policy_type", policy.get("type"))
        return upload_session

    def _upload_content(self, path: Path, session: dict) -> None:
        policy_type = str(session.get("policy_type") or session.get("policyType") or "").lower()
        upload_urls = session.get("upload_urls") or session.get("uploadURLs") or []
        if upload_urls and policy_type == "remote":
            self._upload_remote_direct(path, session)
            return
        if policy_type in {"", "local", "remote"}:
            self._upload_via_cloudreve(path, session)
            return
        if policy_type == "onedrive":
            self._upload_to_onedrive(path, session)
            return
        raise RuntimeError(f"Unsupported Cloudreve storage policy: {policy_type}")

    def _upload_via_cloudreve(self, path: Path, session: dict) -> None:
        session_id = self._session_value(session, "session_id", "sessionID")
        chunk_size = int(
            self._session_value(
                session,
                "chunk_size",
                "chunkSize",
                default=4 * 1024 * 1024,
            )
        )
        with path.open("rb") as file_obj:
            block_id = 0
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                self._request(
                    "POST",
                    f"/file/upload/{session_id}/{block_id}",
                    headers={
                        "Content-Length": str(len(chunk)),
                        "Content-Type": "application/octet-stream",
                    },
                    content=chunk,
                )
                block_id += 1

    def _upload_remote_direct(self, path: Path, session: dict) -> None:
        upload_urls = session.get("upload_urls") or session.get("uploadURLs") or []
        upload_url = upload_urls[0]
        credential = session.get("credential") or ""
        chunk_size = int(
            self._session_value(
                session,
                "chunk_size",
                "chunkSize",
                default=4 * 1024 * 1024,
            )
        )
        with httpx.Client(timeout=60) as client, path.open("rb") as file_obj:
            block_id = 0
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                response = self._send_with_retries(
                    lambda chunk=chunk, block_id=block_id: client.post(
                        upload_url,
                        params={"chunk": block_id},
                        headers={
                            "Authorization": credential,
                            "Content-Length": str(len(chunk)),
                            "Content-Type": "application/octet-stream",
                        },
                        content=chunk,
                    ),
                    f"upload remote chunk {block_id}",
                )
                response.raise_for_status()
                self._raise_cloudreve_error_if_present(response)
                block_id += 1

    def _upload_to_onedrive(self, path: Path, session: dict) -> None:
        upload_urls = session.get("upload_urls") or session.get("uploadURLs") or []
        upload_url = upload_urls[0]
        chunk_size = int(
            self._session_value(
                session,
                "chunk_size",
                "chunkSize",
                default=4 * 1024 * 1024,
            )
        )
        file_size = path.stat().st_size
        with httpx.Client(timeout=60) as client, path.open("rb") as file_obj:
            for start in range(0, file_size, chunk_size):
                chunk = file_obj.read(chunk_size)
                end = start + len(chunk) - 1
                response = self._send_with_retries(
                    lambda chunk=chunk, start=start, end=end: client.put(
                        upload_url,
                        headers={
                            "Content-Range": f"bytes {start}-{end}/{file_size}",
                            "Content-Type": "application/octet-stream",
                        },
                        content=chunk,
                    ),
                    f"upload OneDrive chunk starting at {start}",
                )
                response.raise_for_status()
        callback_secret = session.get("callback_secret") or session.get("callbackSecret")
        if callback_secret:
            session_id = self._session_value(session, "session_id", "sessionID")
            self._request("POST", f"/callback/onedrive/{session_id}/{callback_secret}")

    def _create_link(self, storage_key: str, *, expire: str | None = None) -> str | None:
        if self.config.get("prefer_direct_url"):
            data = self._request(
                "PUT",
                "/file/source",
                json={"uris": [self._cloudreve_uri(storage_key)]},
            )
            if isinstance(data, list) and data:
                return data[0].get("link") or data[0].get("url")
            return None
        data = self._request(
            "PUT",
            "/share",
            json={
                "uri": self._cloudreve_uri(storage_key),
                "downloads": None,
                "expire": duration_seconds(expire) if expire else None,
                "password": None,
                "is_private": False,
                "share_view": None,
                "show_readme": None,
            },
        )
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return data.get("url") or data.get("link") or data.get("share_url")
        return None

    def _download_url(self, storage_key: str) -> str:
        data = self._request(
            "POST",
            "/file/url",
            json={"download": True, "uris": [self._cloudreve_uri(storage_key)]},
        )
        if not isinstance(data, dict):
            raise RuntimeError("Cloudreve download URL response was not an object.")
        urls = data.get("urls") or []
        if not urls:
            raise RuntimeError("Cloudreve did not return a download URL.")
        url = urls[0].get("url")
        if not url:
            raise RuntimeError("Cloudreve download URL response is missing url.")
        return self._absolute_url(url)

    def _request(self, method: str, path: str, **kwargs) -> dict | list | str | None:
        self._ensure_token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.update(self._auth_headers())
        with httpx.Client(base_url=self.base_url, timeout=60) as client:
            response = self._send_with_retries(
                lambda: client.request(method, path, headers=headers, **kwargs),
                f"{method} {path}",
            )
        response.raise_for_status()
        return self._payload_data(response)

    def _ensure_token(self) -> None:
        if self._access_token:
            return
        with httpx.Client(base_url=self.base_url, timeout=60) as client:
            response = self._send_with_retries(
                lambda: client.post(
                    "/session/token",
                    json={
                        "email": self.config["username"],
                        "password": self.config["password"],
                    },
                ),
                "login",
            )
        response.raise_for_status()
        data = self._payload_data(response)
        if not isinstance(data, dict):
            raise RuntimeError("Cloudreve login response did not include token data.")
        token = data.get("token") or {}
        self._access_token = token.get("access_token") or data.get("access_token")
        self._refresh_token = token.get("refresh_token") or data.get("refresh_token")
        if not self._access_token:
            raise RuntimeError("Cloudreve login response did not include an access token.")

    def _auth_headers(self) -> dict[str, str]:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def _remote_file_uri(self, path: Path) -> str:
        root_path = (self.config.get("root_path") or "/").strip("/")
        plain_path = f"/{root_path}/{path.name}" if root_path else f"/{path.name}"
        return self._cloudreve_uri(plain_path)

    def _cloudreve_uri(self, uri: str) -> str:
        if uri.startswith("cloudreve://"):
            normalized = uri
        else:
            normalized = uri if uri.startswith("/") else f"/{uri}"
            normalized = f"cloudreve://my{normalized}"
        while normalized.endswith("//"):
            normalized = normalized[:-1]
        return normalized

    def _api_base_url(self, base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/api/v4"):
            normalized = f"{normalized}/api/v4"
        return normalized

    def _payload_data(self, response: httpx.Response) -> dict | list | str | None:
        if not response.content:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        if isinstance(payload, dict) and payload.get("code") not in (None, 0):
            message = payload.get("msg") or payload.get("message") or "Cloudreve API error"
            raise RuntimeError(str(message))
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def _raise_cloudreve_error_if_present(self, response: httpx.Response) -> None:
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return
        self._payload_data(response)

    def _session_value(self, session: dict, *names: str, default=None):
        for name in names:
            if name in session:
                return session[name]
        if default is not None:
            return default
        raise RuntimeError(f"Cloudreve upload session is missing {names[0]}.")

    def _absolute_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url
        if url.startswith("/"):
            return urljoin(f"{self.site_url}/", url.lstrip("/"))
        return urljoin(f"{self.base_url}/", url)

    def _send_with_retries(
        self,
        send: Callable[[], httpx.Response],
        operation: str,
    ) -> httpx.Response:
        attempts = int(self.config.get("network_retries", 3))
        backoff = float(self.config.get("network_retry_backoff", 0.75))
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return send()
            except _NETWORK_EXCEPTIONS as exc:
                last_error = exc
                if attempt == attempts:
                    break
                sleep(backoff * attempt)
        raise RuntimeError(
            f"Cloudreve network error during {operation}: {last_error}. "
            f"Retried {attempts} time(s)."
        ) from last_error
