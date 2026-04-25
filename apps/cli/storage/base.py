from __future__ import annotations

from pathlib import Path
from typing import Protocol

from linkfile_core.index import FileRecord
from linkfile_core.models import UploadResult


class StorageStrategy(Protocol):
    config: dict

    def test_connection(self) -> None:
        """Raise an exception when the storage method is not usable."""

    def upload_file(self, path: Path, *, expire: str | None = None) -> UploadResult:
        """Upload a local file and return metadata plus fresh URLs."""

    def download_file(self, record: FileRecord, destination: Path) -> Path:
        """Download an indexed file record to a destination path or directory."""

    def delete_file(self, record: FileRecord) -> None:
        """Delete the remote file when supported."""

    def generate_temporary_url(
        self,
        record: FileRecord,
        *,
        expire: str | None = None,
    ) -> str | None:
        """Generate a fresh temporary URL without persisting it."""
