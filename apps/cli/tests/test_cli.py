import shutil
from pathlib import Path
from uuid import uuid4

from linkfile_cli.main import app
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
