from __future__ import annotations

from linkfile_core.storage.base import StorageBackend


class StorageRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, StorageBackend] = {}

    def register(self, backend: StorageBackend) -> None:
        self._backends[backend.id] = backend

    def get(self, backend_id: str) -> StorageBackend:
        return self._backends[backend_id]

    def names(self) -> list[str]:
        return sorted(self._backends)
