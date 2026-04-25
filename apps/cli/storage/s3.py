from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import quote

from linkfile_core.index import FileRecord
from linkfile_core.models import StorageType, UploadResult
from linkfile_core.utils import (
    duration_seconds,
    expires_at_from_duration,
    guess_mime_type,
    sha256_file,
)


class S3Strategy:
    def __init__(self, config: dict) -> None:
        self.config = config

    def test_connection(self) -> None:
        self._client().head_bucket(Bucket=self.config["bucket"])

    def upload_file(self, path: Path, *, expire: str | None = None) -> UploadResult:
        key = self._build_storage_key(path)
        mime_type = guess_mime_type(path)
        content_type = self._normalize_content_type(mime_type)
        extra_args = {"ContentType": content_type} if content_type else None
        client = self._client()
        if extra_args:
            client.upload_file(str(path), self.config["bucket"], key, ExtraArgs=extra_args)
        else:
            client.upload_file(str(path), self.config["bucket"], key)

        return UploadResult(
            file_id=f"file_{uuid.uuid4().hex}",
            name=path.name,
            size=path.stat().st_size,
            mime_type=mime_type,
            storage_method_id=self.config["id"],
            storage_type=StorageType.S3,
            storage_key=key,
            public_url=self._public_url(key),
            raw_url=self._presigned_url(key, expire=expire, content_type=content_type),
            expires_at=expires_at_from_duration(expire),
            metadata={"sha256": sha256_file(path)},
        )

    def download_file(self, record: FileRecord, destination: Path) -> Path:
        target = (
            destination / record.name
            if destination.exists() and destination.is_dir()
            else destination
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        self._client().download_file(self.config["bucket"], record.storage_key, str(target))
        return target

    def delete_file(self, record: FileRecord) -> None:
        self._client().delete_object(Bucket=self.config["bucket"], Key=record.storage_key)

    def generate_temporary_url(
        self,
        record: FileRecord,
        *,
        expire: str | None = None,
    ) -> str | None:
        content_type = self._normalize_content_type(record.mime_type)
        return self._presigned_url(record.storage_key, expire=expire, content_type=content_type)

    def _client(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "S3 support requires boto3. Install LinkFile CLI dependencies first."
            ) from exc

        return boto3.client(
            "s3",
            endpoint_url=self.config.get("endpoint_url") or None,
            region_name=self._region_name(),
            aws_access_key_id=self.config["access_key_id"],
            aws_secret_access_key=self.config["secret_access_key"],
            config=Config(
                s3={
                    "addressing_style": self._addressing_style(),
                }
            ),
        )

    def _build_storage_key(self, path: Path) -> str:
        prefix = (self.config.get("prefix") or "").strip("/")
        safe_name = quote(path.name, safe="")
        key = f"{uuid.uuid4().hex}_{safe_name}"
        return f"{prefix}/{key}" if prefix else key

    def _public_url(self, key: str) -> str | None:
        base_url = (self.config.get("public_base_url") or "").rstrip("/")
        if not base_url:
            return None
        return f"{base_url}/{quote(key, safe='/')}"

    def _presigned_url(
        self,
        key: str,
        *,
        expire: str | None = None,
        content_type: str | None = None,
    ) -> str:
        params = {"Bucket": self.config["bucket"], "Key": key}
        if content_type:
            params["ResponseContentType"] = content_type
        return self._client().generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=duration_seconds(expire),
        )

    def _normalize_content_type(self, mime_type: str | None) -> str | None:
        if not mime_type:
            return None
        if mime_type.startswith("text/"):
            return f"{mime_type}; charset=utf-8"
        if mime_type in {
            "application/json",
            "application/xml",
            "application/javascript",
            "application/ld+json",
            "application/xhtml+xml",
        }:
            return f"{mime_type}; charset=utf-8"
        return mime_type

    def _addressing_style(self) -> str:
        endpoint_url = str(self.config.get("endpoint_url") or "").lower()
        if self.config.get("use_path_style") or ".r2.cloudflarestorage.com" in endpoint_url:
            return "path"
        return "virtual"

    def _region_name(self) -> str | None:
        endpoint_url = str(self.config.get("endpoint_url") or "").lower()
        if ".r2.cloudflarestorage.com" in endpoint_url:
            return "auto"
        return self.config.get("region") or None
