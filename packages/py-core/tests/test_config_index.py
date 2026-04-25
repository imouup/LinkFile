from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from linkfile_core.config import ensure_local_environment, load_config, upsert_storage_method
from linkfile_core.index import LocalIndex
from linkfile_core.models import StorageType, UploadResult


def test_setup_config_and_index_do_not_store_temporary_urls(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    monkeypatch.setenv("LINKFILE_CONFIG_DIR", str(work_dir / "config"))
    monkeypatch.setenv("LINKFILE_DATA_DIR", str(work_dir / "data"))

    try:
        paths = ensure_local_environment()
        index = LocalIndex(paths.index_file)
        index.initialize()

        config = load_config()
        upsert_storage_method(config, {"id": "my-r2", "name": "My R2", "type": "s3"})
        assert config["defaults"]["storage_method_id"] == "my-r2"

        index.add_upload_result(
            UploadResult(
                file_id="file_test",
                name="report.pdf",
                size=123,
                storage_method_id="my-r2",
                storage_type=StorageType.S3,
                storage_key="uploads/report.pdf",
                public_url="https://files.example.com/uploads/report.pdf",
                raw_url="https://temporary.example.com/signature",
                expires_at=datetime.now(UTC),
            )
        )

        record = index.get_file("file_test")
        assert record.public_url == "https://files.example.com/uploads/report.pdf"
        assert "temporary" not in str(record)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
