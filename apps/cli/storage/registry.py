from __future__ import annotations

from storage.base import StorageStrategy
from storage.cloudreve import CloudreveStrategy
from storage.s3 import S3Strategy


def create_strategy(config: dict) -> StorageStrategy:
    storage_type = config.get("type")
    if storage_type == "s3":
        return S3Strategy(config)
    if storage_type == "cloudreve":
        return CloudreveStrategy(config)
    raise ValueError(f"Unsupported storage type: {storage_type}")
