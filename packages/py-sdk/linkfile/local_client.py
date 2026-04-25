from __future__ import annotations

from pathlib import Path

from linkfile_core.config import get_default_paths


class LocalLinkFileClient:
    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or get_default_paths().config_file

    @classmethod
    def from_config(cls) -> "LocalLinkFileClient":
        return cls()

    def upload_file(self, path: str | Path, *, expire: str | None = None) -> None:
        file_path = Path(path)
        raise NotImplementedError(
            f"Offline upload for {file_path} with expire={expire!r} belongs to the v0.1 core loop."
        )
