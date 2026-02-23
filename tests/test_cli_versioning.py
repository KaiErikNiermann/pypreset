"""CLI wiring tests for versioning commands."""

from typer.testing import CliRunner

from pysetup.cli import app

runner = CliRunner()


def test_version_help_lists_commands() -> None:
    """Version command group should be registered."""
    result = runner.invoke(app, ["version", "--help"])

    assert result.exit_code == 0
    assert "release" in result.stdout
    assert "release-version" in result.stdout
    assert "rerun" in result.stdout
    assert "rerelease" in result.stdout
