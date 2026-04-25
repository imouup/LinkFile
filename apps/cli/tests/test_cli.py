import shutil
from pathlib import Path
from uuid import uuid4

from linkfile_cli.main import _print_upload_result, app
from linkfile_core.models import StorageType, UploadResult
from typer.testing import CliRunner

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "LinkFile" in result.output


def test_setup_and_storage_add_s3(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    monkeypatch.setenv("LINKFILE_CONFIG_DIR", str(work_dir / "config"))
    monkeypatch.setenv("LINKFILE_DATA_DIR", str(work_dir / "data"))

    try:
        setup_result = runner.invoke(app, ["setup"])
        assert setup_result.exit_code == 0

        add_result = runner.invoke(
            app,
            [
                "storage",
                "add",
                "s3",
                "--name",
                "my-r2",
                "--endpoint-url",
                "https://example.com",
                "--region",
                "auto",
                "--bucket",
                "bucket",
                "--prefix",
                "uploads",
                "--public-base-url",
                "https://files.example.com",
                "--access-key-id",
                "ak",
                "--secret-access-key",
                "sk",
            ],
        )
        assert add_result.exit_code == 0

        config_text = (work_dir / "config" / "config.json").read_text(encoding="utf-8")
        assert '"type": "s3"' in config_text
        assert '"secret_access_key": "sk"' in config_text
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def test_storage_delete_removes_method_and_updates_default(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    monkeypatch.setenv("LINKFILE_CONFIG_DIR", str(work_dir / "config"))
    monkeypatch.setenv("LINKFILE_DATA_DIR", str(work_dir / "data"))

    try:
        assert runner.invoke(app, ["setup"]).exit_code == 0
        first = [
            "storage",
            "add",
            "s3",
            "--name",
            "first-r2",
            "--endpoint-url",
            "https://example.com",
            "--region",
            "auto",
            "--bucket",
            "bucket",
            "--public-base-url",
            "https://files.example.com",
            "--access-key-id",
            "ak",
            "--secret-access-key",
            "sk",
        ]
        second = [
            "storage",
            "add",
            "s3",
            "--name",
            "second-r2",
            "--endpoint-url",
            "https://example.com",
            "--region",
            "auto",
            "--bucket",
            "bucket",
            "--public-base-url",
            "https://files.example.com",
            "--access-key-id",
            "ak",
            "--secret-access-key",
            "sk",
        ]
        assert runner.invoke(app, first).exit_code == 0
        assert runner.invoke(app, second).exit_code == 0

        delete_result = runner.invoke(app, ["storage", "delete", "first-r2", "--yes"])

        assert delete_result.exit_code == 0
        config_text = (work_dir / "config" / "config.json").read_text(encoding="utf-8")
        assert "first-r2" not in config_text
        assert '"storage_method_id": "second-r2"' in config_text
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def test_upload_text_output_includes_file_id(capsys) -> None:
    _print_upload_result(
        UploadResult(
            file_id="file_test",
            name="report.txt",
            size=5,
            storage_method_id="my-cloud",
            storage_type=StorageType.CLOUDREVE,
            storage_key="cloudreve://my/LinkFile/report.txt",
            raw_url="https://cloud.example.com/d/report",
        ),
        "text",
    )

    output = capsys.readouterr().out
    assert "ID: file_test" in output


def test_upload_runtime_error_is_user_facing(monkeypatch) -> None:
    work_dir = Path.cwd() / "test-runtime" / uuid4().hex
    work_dir.mkdir(parents=True)
    source = work_dir / "report.txt"
    source.write_text("hello", encoding="utf-8")
    monkeypatch.setenv("LINKFILE_CONFIG_DIR", str(work_dir / "config"))
    monkeypatch.setenv("LINKFILE_DATA_DIR", str(work_dir / "data"))

    class FailingStrategy:
        def upload_file(self, file, *, expire=None):
            raise RuntimeError("Cloudreve network error during login: temporary EOF")

    try:
        assert runner.invoke(app, ["setup"], input="n\n").exit_code == 0
        add_result = runner.invoke(
            app,
            [
                "storage",
                "add",
                "cloudreve",
                "--name",
                "my-cloud",
                "--base-url",
                "https://cloud.example.com",
                "--username",
                "user",
                "--password",
                "pass",
            ],
        )
        assert add_result.exit_code == 0
        monkeypatch.setattr("linkfile_cli.main.create_strategy", lambda method: FailingStrategy())

        result = runner.invoke(app, ["upload", str(source), "--storage", "my-cloud"])

        assert result.exit_code == 1
        assert "Upload failed:" in result.output
        assert "Traceback" not in result.output
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
