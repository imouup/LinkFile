from __future__ import annotations

from pathlib import Path

import httpx

from linkfile.models import UploadResult


class LinkFileClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def upload_file(self, path: str | Path, *, expire: str | None = None) -> UploadResult:
        file_path = Path(path)
        with file_path.open("rb") as file_obj:
            response = httpx.post(
                f"{self.base_url}/api/files/upload",
                headers=self._headers(),
                data={"expire": expire} if expire else None,
                files={"file": (file_path.name, file_obj)},
                timeout=60,
            )
        response.raise_for_status()
        return UploadResult.model_validate(response.json())
