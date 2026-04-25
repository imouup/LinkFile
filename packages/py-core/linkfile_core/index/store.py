from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linkfile_core.config import get_default_paths
from linkfile_core.models import UploadResult


@dataclass(frozen=True)
class FileRecord:
    file_id: str
    name: str
    size: int
    storage_method_id: str
    storage_type: str
    storage_key: str
    mime_type: str | None
    public_url: str | None
    share_url: str | None
    expires_at: str | None
    created_at: str
    updated_at: str
    metadata: dict[str, Any]


class LocalIndex:
    def __init__(self, index_file: Path | None = None) -> None:
        self.index_file = index_file or get_default_paths().index_file

    def initialize(self) -> None:
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    storage_method_id TEXT NOT NULL,
                    storage_type TEXT NOT NULL,
                    storage_key TEXT NOT NULL,
                    mime_type TEXT,
                    public_url TEXT,
                    share_url TEXT,
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

    def add_upload_result(self, result: UploadResult) -> FileRecord:
        self.initialize()
        now = datetime.now(UTC).isoformat()
        record = FileRecord(
            file_id=result.file_id,
            name=result.name,
            size=result.size,
            storage_method_id=result.storage_method_id,
            storage_type=str(result.storage_type),
            storage_key=result.storage_key,
            mime_type=result.mime_type,
            public_url=result.public_url,
            share_url=result.share_url,
            expires_at=result.expires_at.isoformat() if result.expires_at else None,
            created_at=now,
            updated_at=now,
            metadata=result.metadata,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (
                    file_id, name, size, storage_method_id, storage_type, storage_key,
                    mime_type, public_url, share_url, expires_at, created_at, updated_at,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.file_id,
                    record.name,
                    record.size,
                    record.storage_method_id,
                    record.storage_type,
                    record.storage_key,
                    record.mime_type,
                    record.public_url,
                    record.share_url,
                    record.expires_at,
                    record.created_at,
                    record.updated_at,
                    json.dumps(record.metadata),
                ),
            )
        return record

    def list_files(self) -> list[FileRecord]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_id, name, size, storage_method_id, storage_type, storage_key,
                       mime_type, public_url, share_url, expires_at, created_at, updated_at,
                       metadata_json
                FROM files
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_file(self, file_id: str) -> FileRecord:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT file_id, name, size, storage_method_id, storage_type, storage_key,
                       mime_type, public_url, share_url, expires_at, created_at, updated_at,
                       metadata_json
                FROM files
                WHERE file_id = ?
                """,
                (file_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"File record not found: {file_id}")
        return self._row_to_record(row)

    def delete_file(self, file_id: str) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM files WHERE file_id = ?", (file_id,))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.index_file)

    def _row_to_record(self, row: tuple[Any, ...]) -> FileRecord:
        return FileRecord(
            file_id=row[0],
            name=row[1],
            size=row[2],
            storage_method_id=row[3],
            storage_type=row[4],
            storage_key=row[5],
            mime_type=row[6],
            public_url=row[7],
            share_url=row[8],
            expires_at=row[9],
            created_at=row[10],
            updated_at=row[11],
            metadata=json.loads(row[12] or "{}"),
        )
