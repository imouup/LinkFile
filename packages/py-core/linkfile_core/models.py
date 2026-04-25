from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class StorageType(StrEnum):
    S3 = "s3"
    CLOUDREVE = "cloudreve"
    LOCAL_SERVER = "local-server"
    WEBDAV = "webdav"
    ONEDRIVE = "onedrive"


class ShareDeliveryMode(StrEnum):
    PUBLIC_URL = "public_url"
    PRESIGNED_URL = "presigned_url"
    CLOUDREVE_DIRECT_URL = "cloudreve_direct_url"
    CLOUDREVE_SHARE_URL = "cloudreve_share_url"
    LOCAL_SERVER_URL = "local_server_url"
    LINKFILE_REDIRECT = "linkfile_redirect"
    LINKFILE_PROXY = "linkfile_proxy"


class UploadResult(BaseModel):
    file_id: str
    name: str
    size: int
    storage_method_id: str
    storage_type: StorageType | str
    storage_key: str
    mime_type: str | None = None
    share_url: str | None = None
    raw_url: str | None = None
    public_url: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
