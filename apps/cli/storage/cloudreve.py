from __future__ import annotations

import uuid
from pathlib import Path

from linkfile_core.index import FileRecord
from linkfile_core.models import ShareDeliveryMode, StorageType, UploadResult
from linkfile_core.utils import expires_at_from_duration, guess_mime_type, sha256_file


class CloudreveStrategy:
    """Cloudreve storage backend using the cloudreve SDK (v3/v4)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._client: object | None = None
        self._api_version: str | None = None

    def test_connection(self) -> None:
        client, _ = self._client_instance()
        root_path = (self.config.get("root_path") or "/").rstrip("/") or "/"
        if hasattr(client, "list"):
            try:
                client.list(root_path)
            except Exception as exc:
                if root_path != "/" and self._is_missing_path_error(exc):
                    # Create the root folder on first run so uploads can proceed.
                    self._ensure_remote_folder(client, root_path)
                    client.list(root_path)
                else:
                    raise

    def upload_file(self, path: Path, *, expire: str | None = None) -> UploadResult:
        client, api_version = self._client_instance()
        remote_path = self._remote_path(path)
        storage_key = self._upload(client, api_version, path, remote_path)
        link = self._create_link(client, storage_key)
        return UploadResult(
            file_id=f"file_{uuid.uuid4().hex}",
            name=path.name,
            size=path.stat().st_size,
            mime_type=guess_mime_type(path),
            storage_method_id=self.config["id"],
            storage_type=StorageType.CLOUDREVE,
            storage_key=storage_key,
            share_url=None,
            raw_url=link,
            expires_at=expires_at_from_duration(expire),
            metadata={
                "sha256": sha256_file(path),
                "delivery_mode": ShareDeliveryMode.CLOUDREVE_DIRECT_URL,
                "cloudreve_api_version": api_version,
            },
        )

    def download_file(self, record: FileRecord, destination: Path) -> Path:
        client, api_version = self._client_instance()
        target = (
            destination / record.name
            if destination.exists() and destination.is_dir()
            else destination
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if api_version == "v4":
            # Legacy v3 uploads store an ID, so fall back to the v3 client for those.
            if not self._is_v4_uri(record.storage_key):
                legacy_client, _ = self._login_v3()
                legacy_client.download(record.storage_key, str(target))
                return target
            uri = self._normalize_v4_uri(record.storage_key)
            url = self._download_url(client, uri)
            if not url:
                raise RuntimeError("Cloudreve did not return a download URL.")
            self._download_from_url(url, target)
        else:
            client.download(record.storage_key, str(target))
        return target

    def delete_file(self, record: FileRecord) -> None:
        client, api_version = self._client_instance()
        if api_version == "v4":
            if not self._is_v4_uri(record.storage_key):
                legacy_client, _ = self._login_v3()
                legacy_client.delete(record.storage_key, is_dir=False)
                return
            client.delete(self._normalize_v4_uri(record.storage_key))
        else:
            client.delete(record.storage_key, is_dir=False)

    def generate_temporary_url(
        self,
        record: FileRecord,
        *,
        expire: str | None = None,
    ) -> str | None:
        client, api_version = self._client_instance()
        if api_version == "v4" and not self._is_v4_uri(record.storage_key):
            legacy_client, _ = self._login_v3()
            return self._create_link(legacy_client, record.storage_key)
        uri = (
            self._normalize_v4_uri(record.storage_key)
            if api_version == "v4"
            else record.storage_key
        )
        return self._create_link(client, uri)

    def _client_instance(self) -> tuple[object, str]:
        if self._client and self._api_version:
            return self._client, self._api_version
        api_version = str(self.config.get("api_version") or "auto").lower()
        if api_version in {"v4", "4"}:
            return self._login_v4()
        if api_version in {"v3", "3"}:
            return self._login_v3()
        try:
            return self._login_v4()
        except Exception as exc_v4:
            try:
                return self._login_v3()
            except Exception as exc_v3:
                raise RuntimeError(
                    f"Cloudreve login failed for both v4 and v3 clients. Last v4 error: {exc_v4}"
                ) from exc_v3

    def _login_v4(self) -> tuple[object, str]:
        CloudreveV4 = self._cloudreve_class("CloudreveV4")
        client = CloudreveV4(self.config["base_url"])
        client.login(self.config["username"], self.config["password"])
        self._client = client
        self._api_version = "v4"
        return client, "v4"

    def _login_v3(self) -> tuple[object, str]:
        Cloudreve = self._cloudreve_class("Cloudreve")
        client = Cloudreve(self.config["base_url"])
        client.login(self.config["username"], self.config["password"])
        self._client = client
        self._api_version = "v3"
        return client, "v3"

    def _cloudreve_class(self, name: str):
        try:
            import cloudreve
        except ImportError as exc:
            raise RuntimeError(
                "Cloudreve support requires the cloudreve package. Install it with: pip install cloudreve"
            ) from exc
        return getattr(cloudreve, name)

    def _upload(
        self,
        client: object,
        api_version: str,
        path: Path,
        remote_path: str,
    ) -> str:
        if api_version == "v4":
            client.upload(str(path), remote_path)
            return remote_path
        client.upload(remote_path, str(path))
        return client.get_id(remote_path)

    def _create_link(
        self,
        client: object,
        storage_key: str,
        *,
        expire: str | None = None,
    ) -> str | None:
        # Direct links are returned; expire is ignored by design.
        _ = expire
        return self._extract_link(client.get_source_url(storage_key))

    def _download_url(self, client: object, storage_key: str) -> str | None:
        if hasattr(client, "get_download_url"):
            return self._extract_link(client.get_download_url(storage_key))
        if hasattr(client, "get_source_url"):
            return self._extract_link(client.get_source_url(storage_key))
        return None

    def _download_from_url(self, url: str, target: Path) -> None:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is required to download Cloudreve files.") from exc
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with target.open("wb") as file_obj:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file_obj.write(chunk)

    def _ensure_remote_folder(self, client: object, root_path: str) -> None:
        if hasattr(client, "create_folder"):
            client.create_folder(root_path)
        elif hasattr(client, "create_dir"):
            client.create_dir(root_path)
        else:
            raise RuntimeError("Cloudreve client does not support folder creation.")

    def _is_missing_path_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "path not exist" in message or "40016" in message

    def _is_v4_uri(self, storage_key: str) -> bool:
        return storage_key.startswith("cloudreve://") or storage_key.startswith("/")

    def _normalize_v4_uri(self, storage_key: str) -> str:
        # v4 expects cloudreve://my/... URIs.
        if storage_key.startswith("cloudreve://"):
            return storage_key.rstrip("/")
        if not storage_key.startswith("/"):
            storage_key = f"/{storage_key}"
        uri = f"cloudreve://my{storage_key}"
        return uri.rstrip("/")

    def _extract_link(self, value: object) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return (
                value.get("url")
                or value.get("link")
                or value.get("share_url")
                or value.get("download_url")
            )
        if isinstance(value, list) and value:
            return self._extract_link(value[0])
        return None

    def _remote_path(self, path: Path) -> str:
        root_path = (self.config.get("root_path") or "/").rstrip("/")
        return f"{root_path}/{path.name}" if root_path else f"/{path.name}"
