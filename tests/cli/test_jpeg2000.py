from typer.testing import CliRunner

from project_prototype.apps.jpeg2000 import app as jpeg2000_app


def test_jpeg2000_command(runner: CliRunner) -> None:
    result = runner.invoke(jpeg2000_app, [])
    assert result.exc_info is not None
    assert isinstance(result.exc_info[1], NotImplementedError)
    assert result.exit_code == 1
