from __future__ import annotations

import sys
import types
from pathlib import Path
from uuid import uuid4

from linkfile_core.index import FileRecord
from storage.cloudreve import CloudreveStrategy
from storage.s3 import S3Strategy


def test_s3_strategy_upload_and_presign_without_persisting(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    source = work_dir / "report.txt"
    source.write_text("hello", encoding="utf-8")

    class FakeS3Client:
        uploaded: tuple[str, str, str] | None = None

        def head_bucket(self, **kwargs):
            assert kwargs["Bucket"] == "bucket"

        def upload_file(self, filename, bucket, key, ExtraArgs=None):
            self.uploaded = (filename, bucket, key)
            assert ExtraArgs["ContentType"] == "text/plain; charset=utf-8"

        def generate_presigned_url(self, operation, Params, ExpiresIn):
            assert operation == "get_object"
            assert Params["Bucket"] == "bucket"
            assert Params["ResponseContentType"] == "text/plain; charset=utf-8"
            assert ExpiresIn == 3600
            return f"https://signed.example.com/{Params['Key']}"

        def download_file(self, bucket, key, filename):
            pass

        def delete_object(self, **kwargs):
            pass

    fake_client = FakeS3Client()
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        types.SimpleNamespace(client=lambda *a, **k: fake_client),
    )
    monkeypatch.setitem(
        sys.modules,
        "botocore.config",
        types.SimpleNamespace(Config=lambda **kwargs: kwargs),
    )

    strategy = S3Strategy(
        {
            "id": "my-r2",
            "type": "s3",
            "bucket": "bucket",
            "prefix": "uploads",
            "region": "auto",
            "endpoint_url": "https://example.com",
            "access_key_id": "ak",
            "secret_access_key": "sk",
            "public_base_url": "https://files.example.com",
            "use_path_style": True,
        }
    )

    try:
        result = strategy.upload_file(source)

        assert result.storage_method_id == "my-r2"
        assert result.raw_url is not None
        assert result.public_url is not None
        assert result.storage_key.startswith("uploads/")
    finally:
        source.unlink(missing_ok=True)
        work_dir.rmdir()


def test_s3_strategy_forces_path_style_for_r2(monkeypatch) -> None:
    captured_config: dict | None = None
    captured_region: str | None = None

    def fake_client(*args, **kwargs):
        nonlocal captured_config, captured_region
        captured_config = kwargs["config"]
        captured_region = kwargs["region_name"]

        class FakeS3Client:
            pass

        return FakeS3Client()

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=fake_client))
    monkeypatch.setitem(
        sys.modules,
        "botocore.config",
        types.SimpleNamespace(Config=lambda **kwargs: kwargs),
    )

    strategy = S3Strategy(
        {
            "id": "linkfile-r2",
            "type": "s3",
            "bucket": "linkfile",
            "prefix": "uploads",
            "region": "apac",
            "endpoint_url": "https://7600788a34e48fa8502a3f1765b229a3.r2.cloudflarestorage.com",
            "access_key_id": "ak",
            "secret_access_key": "sk",
            "public_base_url": "",
            "use_path_style": False,
        }
    )

    strategy._client()

    assert captured_config == {"s3": {"addressing_style": "path"}}
    assert captured_region == "auto"


def test_cloudreve_strategy_upload_uses_source_url(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    source = work_dir / "report.txt"
    source.write_text("hello", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    class FakeCloudreveV4:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def login(self, username: str, password: str) -> None:
            calls.append(("login", username))

        def list(self, path: str):
            calls.append(("list", path))
            return []

        def upload(self, local_path: str, remote_path: str) -> None:
            calls.append(("upload", remote_path))

        def get_source_url(self, uri: str):
            calls.append(("get_source_url", uri))
            return "https://cloud.example.com/d/report"

    class FakeCloudreveV3:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def login(self, username: str, password: str) -> None:
            raise RuntimeError("v3 should not be used in this test")

    monkeypatch.setitem(
        sys.modules,
        "cloudreve",
        types.SimpleNamespace(Cloudreve=FakeCloudreveV3, CloudreveV4=FakeCloudreveV4),
    )

    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
            "api_version": "v4",
        }
    )

    try:
        result = strategy.upload_file(source)

        assert result.share_url is None
        assert result.raw_url == "https://cloud.example.com/d/report"
        assert ("login", "user") in calls
        assert ("upload", "/LinkFile/report.txt") in calls
    finally:
        source.unlink(missing_ok=True)
        work_dir.rmdir()


def test_cloudreve_generate_temporary_url_uses_direct_link() -> None:
    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": False,
            "api_version": "v4",
        }
    )

    class FakeCloudreveClient:
        def get_source_url(self, uri: str):
            return "https://cloud.example.com/d/report"

    strategy._client = FakeCloudreveClient()
    strategy._api_version = "v4"
    record = FileRecord(
        file_id="file_1",
        name="report.txt",
        size=5,
        storage_method_id="my-cloud",
        storage_type="cloudreve",
        storage_key="/LinkFile/report.txt",
        mime_type="text/plain",
        public_url=None,
        share_url="https://cloud.example.com/s/report",
        expires_at=None,
        created_at="now",
        updated_at="now",
        metadata={},
    )

    assert strategy.generate_temporary_url(record) == "https://cloud.example.com/d/report"
