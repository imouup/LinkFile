from typer.testing import CliRunner

from linkfile_cli.main import app


def test_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "LinkFile" in result.output
