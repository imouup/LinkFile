from __future__ import annotations

import sys
import types
from pathlib import Path
from uuid import uuid4

import httpx
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

    def response(method: str, path: str, payload: dict | list | None) -> httpx.Response:
        if payload is None:
            return httpx.Response(204, request=httpx.Request(method, path))
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": payload},
            request=httpx.Request(method, path),
        )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, path, **kwargs):
            calls.append(("POST", path))
            if path == "/session/token":
                return response(
                    "POST",
                    path,
                    {"token": {"access_token": "access", "refresh_token": "refresh"}},
                )
            return self.request("POST", path, **kwargs)

        def request(self, method, path, **kwargs):
            calls.append((method, path))
            if method == "GET" and path == "/file":
                return response(
                    "GET",
                    path,
                    {"storage_policy": {"id": "policy", "type": "local"}},
                )
            if method == "PUT" and path == "/file/upload":
                return response(
                    "PUT",
                    path,
                    {"session_id": "session", "chunk_size": 1024},
                )
            if method == "POST" and path == "/file/upload/session/0":
                return response("POST", path, None)
            if method == "PUT" and path == "/file/source":
                return response(
                    "PUT",
                    path,
                    [{"link": "https://cloud.example.com/d/report"}],
                )
            return httpx.Response(404, request=httpx.Request(method, path))

    monkeypatch.setattr(httpx, "Client", FakeClient)

    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
        }
    )

    try:
        result = strategy.upload_file(source)

        assert result.share_url is None
        assert result.raw_url == "https://cloud.example.com/d/report"
        assert ("POST", "/session/token") in calls
        assert ("PUT", "/file/upload") in calls
        assert ("POST", "/file/upload/session/0") in calls
        assert ("PUT", "/file/source") in calls
    finally:
        source.unlink(missing_ok=True)
        work_dir.rmdir()


def test_cloudreve_v4_upload_creates_missing_root_dir(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    source = work_dir / "report.txt"
    source.write_text("hello", encoding="utf-8")
    calls: list[tuple[str, str]] = []
    created_uris: list[str] = []
    list_attempts = 0

    def response(
        method: str,
        path: str,
        payload: dict | list | str | None,
        *,
        code: int = 0,
        message: str = "ok",
    ) -> httpx.Response:
        if payload is None and code == 0:
            return httpx.Response(204, request=httpx.Request(method, path))
        return httpx.Response(
            200,
            json={"code": code, "msg": message, "data": payload},
            request=httpx.Request(method, path),
        )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, path, **kwargs):
            calls.append(("POST", path))
            if path == "/session/token":
                return response(
                    "POST",
                    path,
                    {"token": {"access_token": "access", "refresh_token": "refresh"}},
                )
            return self.request("POST", path, **kwargs)

        def request(self, method, path, **kwargs):
            nonlocal list_attempts
            calls.append((method, path))
            if method == "GET" and path == "/file":
                list_attempts += 1
                if list_attempts == 1:
                    return response(
                        "GET",
                        path,
                        None,
                        code=40016,
                        message="Path not exist",
                    )
                return response(
                    "GET",
                    path,
                    {"storage_policy": {"id": "policy", "type": "local"}},
                )
            if method == "POST" and path == "/file/create":
                created_uris.append(kwargs["json"]["uri"])
                return response("POST", path, {})
            if method == "PUT" and path == "/file/upload":
                return response(
                    "PUT",
                    path,
                    {"session_id": "session", "chunk_size": 1024},
                )
            if method == "POST" and path == "/file/upload/session/0":
                return response("POST", path, None)
            if method == "PUT" and path == "/file/source":
                return response(
                    "PUT",
                    path,
                    [{"link": "https://cloud.example.com/d/report"}],
                )
            return httpx.Response(404, request=httpx.Request(method, path))

    monkeypatch.setattr(httpx, "Client", FakeClient)

    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
        }
    )

    try:
        result = strategy.upload_file(source)

        assert result.storage_key == "cloudreve://my/LinkFile/report.txt"
        assert result.raw_url == "https://cloud.example.com/d/report"
        assert created_uris == ["cloudreve://my/LinkFile"]
        assert ("POST", "/file/create") in calls
        assert ("PUT", "/file/upload") in calls
    finally:
        source.unlink(missing_ok=True)
        work_dir.rmdir()


def test_cloudreve_download_url_normalization() -> None:
    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
        }
    )

    assert (
        strategy._absolute_url("https://cdn.example.com/file", strategy.base_url_v4)
        == "https://cdn.example.com/file"
    )
    assert strategy._absolute_url("/api/v4/file/download/x", strategy.base_url_v4) == (
        "https://cloud.example.com/api/v4/file/download/x"
    )
    assert strategy._absolute_url("file/download/x", strategy.base_url_v4) == (
        "https://cloud.example.com/api/v4/file/download/x"
    )


def test_cloudreve_v3_upload_uses_file_id(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    source = work_dir / "report.txt"
    source.write_text("hello", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def response(method: str, path: str, payload: dict | list | str | None) -> httpx.Response:
        request_url = path
        if path.startswith("/"):
            request_url = f"https://cloud.example.com/api/v3{path}"
        if payload is None:
            return httpx.Response(204, request=httpx.Request(method, request_url))
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": payload},
            request=httpx.Request(method, request_url),
        )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, path, **kwargs):
            calls.append(("POST", path))
            if path == "/user/session":
                return response("POST", path, {"user": "ok"})
            return self.request("POST", path, **kwargs)

        def request(self, method, path, **kwargs):
            calls.append((method, path))
            if method == "GET" and path.startswith("/directory"):
                return response(
                    "GET",
                    path,
                    {
                        "policy": {"id": "policy", "type": "local"},
                        "objects": [{"id": "file123", "name": "report.txt"}],
                    },
                )
            if method == "PUT" and path == "/file/upload":
                return response(
                    "PUT",
                    path,
                    {"sessionID": "session", "chunkSize": 1024},
                )
            if method == "POST" and path == "/file/upload/session/0":
                return response("POST", path, None)
            if method == "POST" and path == "/file/source":
                return response("POST", path, [{"url": "https://cloud.example.com/d/report"}])
            return httpx.Response(404, request=httpx.Request(method, path))

    monkeypatch.setattr(httpx, "Client", FakeClient)

    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
            "api_version": "v3",
        }
    )

    try:
        result = strategy.upload_file(source)

        assert result.storage_key == "file123"
        assert result.raw_url == "https://cloud.example.com/d/report"
        assert ("POST", "/user/session") in calls
        assert ("PUT", "/file/upload") in calls
        assert ("POST", "/file/upload/session/0") in calls
    finally:
        source.unlink(missing_ok=True)
        work_dir.rmdir()


def test_cloudreve_retries_transient_network_errors() -> None:
    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
            "network_retries": 2,
            "network_retry_backoff": 0,
        }
    )
    attempts = 0

    def flaky_send() -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary EOF")
        return httpx.Response(200, request=httpx.Request("GET", "https://cloud.example.com"))

    response = strategy._send_with_retries(flaky_send, "test request")

    assert response.status_code == 200
    assert attempts == 2


def test_cloudreve_delete_uses_v4_file_payload(monkeypatch) -> None:
    captured: dict | None = None

    def response(method: str, path: str, payload: dict) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": payload},
            request=httpx.Request(method, path),
        )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, path, **kwargs):
            return response(
                "POST",
                path,
                {"token": {"access_token": "access", "refresh_token": "refresh"}},
            )

        def request(self, method, path, **kwargs):
            nonlocal captured
            if method == "DELETE" and path == "/file":
                captured = kwargs["json"]
                return response("DELETE", path, {})
            return httpx.Response(404, request=httpx.Request(method, path))

    monkeypatch.setattr(httpx, "Client", FakeClient)
    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": True,
        }
    )
    record = FileRecord(
        file_id="file_1",
        name="report.txt",
        size=5,
        storage_method_id="my-cloud",
        storage_type="cloudreve",
        storage_key="cloudreve://my/LinkFile/report.txt",
        mime_type="text/plain",
        public_url=None,
        share_url=None,
        expires_at=None,
        created_at="now",
        updated_at="now",
        metadata={},
    )

    strategy.delete_file(record)

    assert captured == {
        "uris": ["cloudreve://my/LinkFile/report.txt"],
        "unlink": False,
        "trash_bin": False,
    }


def test_cloudreve_returns_existing_share_for_non_direct_links() -> None:
    strategy = CloudreveStrategy(
        {
            "id": "my-cloud",
            "type": "cloudreve",
            "base_url": "https://cloud.example.com",
            "username": "user",
            "password": "pass",
            "root_path": "/LinkFile",
            "prefer_direct_url": False,
        }
    )
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

    assert strategy.generate_temporary_url(record) == "https://cloud.example.com/s/report"
