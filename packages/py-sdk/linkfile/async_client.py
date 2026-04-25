from __future__ import annotations

from pathlib import Path

import httpx

from linkfile.models import UploadResult


class AsyncLinkFileClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    async def upload_file(self, path: str | Path, *, expire: str | None = None) -> UploadResult:
        file_path = Path(path)
        async with httpx.AsyncClient(timeout=60) as client:
            with file_path.open("rb") as file_obj:
                response = await client.post(
                    f"{self.base_url}/api/files/upload",
                    headers=self._headers(),
                    data={"expire": expire} if expire else None,
                    files={"file": (file_path.name, file_obj)},
                )
        response.raise_for_status()
        return UploadResult.model_validate(response.json())
