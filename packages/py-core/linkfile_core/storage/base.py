from __future__ import annotations

from pathlib import Path
from typing import Protocol

from linkfile_core.models import UploadResult


class StorageBackend(Protocol):
    id: str

    def upload_file(self, path: Path, *, expire: str | None = None) -> UploadResult:
        """Upload a file and return persistent metadata plus any fresh share URL."""
