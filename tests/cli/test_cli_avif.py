from typer.testing import CliRunner

from project_prototype.cli import avif_app


def test_avif_command(runner: CliRunner) -> None:
    result = runner.invoke(avif_app, [])
    assert result.exc_info is not None
    assert isinstance(result.exc_info[1], NotImplementedError)
    assert result.exit_code == 1
