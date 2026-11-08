from typer.testing import CliRunner

from project_prototype.apps.jpeg import app as jpeg_app


def test_jpeg_command(runner: CliRunner) -> None:
    result = runner.invoke(jpeg_app, [])
    assert result.exit_code == 2
