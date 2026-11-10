from typer.testing import CliRunner

from project_prototype.apps.webp import app as webp_app


def test_webp_command(runner: CliRunner) -> None:
    result = runner.invoke(webp_app, [])
    assert result.exc_info is not None
    assert isinstance(result.exc_info[1], NotImplementedError)
    assert result.exit_code == 1
