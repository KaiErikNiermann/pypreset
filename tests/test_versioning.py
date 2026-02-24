"""Tests for versioning assistance."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from pypreset.versioning import VersioningAssistant, VersioningError


@dataclass(frozen=True)
class RecordedCommand:
    """Record a command invocation for assertions."""

    args: list[str]
    check: bool


class FakeRunner:
    """Fake command runner for versioning tests."""

    def __init__(self, outputs: dict[tuple[str, ...], str] | None = None) -> None:
        self.outputs = outputs or {}
        self.commands: list[RecordedCommand] = []

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.commands.append(RecordedCommand(args=args, check=check))
        stdout = self.outputs.get(tuple(args), "")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


def test_release_bump_flow_uses_expected_commands() -> None:
    """Release uses poetry bump + release commands in order."""
    outputs = {("poetry", "version", "--short"): "1.2.3\n"}
    runner = FakeRunner(outputs=outputs)
    assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

    version = assistant.release("bump=minor")

    assert version == "1.2.3"
    assert [cmd.args for cmd in runner.commands] == [
        ["poetry", "version", "minor"],
        ["poetry", "version", "--short"],
        ["git", "add", "pyproject.toml"],
        ["git", "add", "-f", "poetry.lock"],
        ["git", "commit", "-m", "chore(release): v1.2.3"],
        ["git", "push"],
        ["git", "tag", "v1.2.3"],
        ["git", "push", "origin", "v1.2.3"],
        ["gh", "release", "create", "v1.2.3", "--title", "v1.2.3", "--generate-notes"],
    ]


def test_release_version_flow_uses_explicit_version() -> None:
    """Release-version uses the explicit version value."""
    runner = FakeRunner()
    assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

    version = assistant.release_version("version=2.0.0")

    assert version == "2.0.0"
    assert runner.commands[0].args == ["poetry", "version", "2.0.0"]
    assert runner.commands[1].args == ["git", "add", "pyproject.toml"]
    assert runner.commands[2].args == ["git", "add", "-f", "poetry.lock"]
    assert runner.commands[-1].args == [
        "gh",
        "release",
        "create",
        "v2.0.0",
        "--title",
        "v2.0.0",
        "--generate-notes",
    ]


def test_rerun_allows_tag_delete_failures() -> None:
    """Rerun ignores failures for tag delete steps."""
    runner = FakeRunner()
    assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

    assistant.rerun("1.2.3")

    assert [cmd.args for cmd in runner.commands] == [
        ["git", "push"],
        ["git", "tag", "-d", "v1.2.3"],
        ["git", "push", "--delete", "origin", "v1.2.3"],
        ["git", "tag", "v1.2.3"],
        ["git", "push", "origin", "v1.2.3"],
    ]
    assert runner.commands[1].check is False
    assert runner.commands[2].check is False


def test_rerelease_deletes_then_recreates_release() -> None:
    """Rerelease deletes GH release then re-tags and creates a new one."""
    runner = FakeRunner()
    assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

    assistant.rerelease("1.2.3")

    assert runner.commands[0].args == ["gh", "release", "delete", "v1.2.3", "-y"]
    assert runner.commands[0].check is False
    assert runner.commands[-1].args == [
        "gh",
        "release",
        "create",
        "v1.2.3",
        "--title",
        "v1.2.3",
        "--generate-notes",
    ]


def test_release_raises_when_version_missing() -> None:
    """Release should error if poetry returns an empty version."""
    outputs = {("poetry", "version", "--short"): ""}
    runner = FakeRunner(outputs=outputs)
    assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

    with pytest.raises(VersioningError):
        assistant.release("patch")


# --------------------------------------------------------------------------
# sync_server_file tests
# --------------------------------------------------------------------------


class TestSyncServerFile:
    """Tests for the sync_server_file standalone function."""

    def test_updates_single_version_field(self, tmp_path: Path) -> None:
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        server.write_text('{\n  "name": "test",\n  "version": "0.1.0"\n}\n')

        count = sync_server_file(server, "2.0.0")

        assert count == 1
        import json

        data = json.loads(server.read_text())
        assert data["version"] == "2.0.0"

    def test_updates_multiple_version_fields(self, tmp_path: Path) -> None:
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        content = '{\n  "version": "0.1.0",\n  "packages": [{"version": "0.1.0"}]\n}\n'
        server.write_text(content)

        count = sync_server_file(server, "3.0.0")

        assert count == 2
        text = server.read_text()
        assert text.count('"3.0.0"') == 2
        assert '"0.1.0"' not in text

    def test_preserves_formatting(self, tmp_path: Path) -> None:
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        original = '{\n  "name": "test",\n  "version": "1.0.0",\n  "other": true\n}\n'
        server.write_text(original)

        sync_server_file(server, "2.0.0")

        result = server.read_text()
        expected = '{\n  "name": "test",\n  "version": "2.0.0",\n  "other": true\n}\n'
        assert result == expected

    def test_no_version_field_returns_zero(self, tmp_path: Path) -> None:
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        server.write_text('{"name": "test"}\n')

        count = sync_server_file(server, "1.0.0")

        assert count == 0
        assert server.read_text() == '{"name": "test"}\n'

    def test_handles_version_with_spaces(self, tmp_path: Path) -> None:
        """Handles JSON with spaces around the colon."""
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        server.write_text('{"version" : "0.1.0"}\n')

        count = sync_server_file(server, "1.0.0")

        assert count == 1
        assert '"1.0.0"' in server.read_text()

    def test_real_server_json_format(self, tmp_path: Path) -> None:
        """Test with the actual server.json format used by the project."""
        from pypreset.versioning import sync_server_file

        server = tmp_path / "server.json"
        server.write_text(
            "{\n"
            '  "$schema": "https://static.modelcontextprotocol.io/schemas/server.schema.json",\n'
            '  "name": "io.github.user/project",\n'
            '  "version": "0.2.0",\n'
            '  "packages": [\n'
            "    {\n"
            '      "registryType": "pypi",\n'
            '      "identifier": "project",\n'
            '      "version": "0.2.0"\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

        count = sync_server_file(server, "0.3.0")

        assert count == 2
        text = server.read_text()
        assert text.count('"0.3.0"') == 2
        assert '"0.2.0"' not in text


# --------------------------------------------------------------------------
# VersioningAssistant server_file integration tests
# --------------------------------------------------------------------------


class TestVersioningAssistantServerFile:
    """Tests for VersioningAssistant with server_file option."""

    def test_release_syncs_and_stages_server_file(self, tmp_path: Path) -> None:
        """Release with server_file syncs version and adds file to git."""
        server = tmp_path / "server.json"
        server.write_text('{"version": "0.1.0"}\n')

        outputs = {("poetry", "version", "--short"): "1.2.3\n"}
        runner = FakeRunner(outputs=outputs)
        assistant = VersioningAssistant(
            Path("."), runner=runner, preflight=False, server_file=server
        )

        assistant.release("minor")

        # Server file should be updated
        assert '"1.2.3"' in server.read_text()

        # git add for server file should be in the commands
        cmd_args = [cmd.args for cmd in runner.commands]
        assert ["git", "add", str(server)] in cmd_args

        # Server file add should come after poetry.lock add, before commit
        lock_idx = next(
            i
            for i, c in enumerate(runner.commands)
            if c.args == ["git", "add", "-f", "poetry.lock"]
        )
        server_idx = next(
            i for i, c in enumerate(runner.commands) if c.args == ["git", "add", str(server)]
        )
        commit_idx = next(i for i, c in enumerate(runner.commands) if "commit" in c.args[1])
        assert lock_idx < server_idx < commit_idx

    def test_release_version_syncs_server_file(self, tmp_path: Path) -> None:
        """Release-version with server_file syncs the explicit version."""
        server = tmp_path / "server.json"
        server.write_text('{"version": "0.1.0"}\n')

        runner = FakeRunner()
        assistant = VersioningAssistant(
            Path("."), runner=runner, preflight=False, server_file=server
        )

        assistant.release_version("2.0.0")

        assert '"2.0.0"' in server.read_text()
        cmd_args = [cmd.args for cmd in runner.commands]
        assert ["git", "add", str(server)] in cmd_args

    def test_release_without_server_file_unchanged(self) -> None:
        """Release without server_file behaves exactly as before."""
        outputs = {("poetry", "version", "--short"): "1.0.0\n"}
        runner = FakeRunner(outputs=outputs)
        assistant = VersioningAssistant(Path("."), runner=runner, preflight=False)

        assistant.release("patch")

        cmd_args = [cmd.args for cmd in runner.commands]
        # No server file add command
        assert all("server" not in str(c) for c in cmd_args)

    def test_nonexistent_server_file_raises(self, tmp_path: Path) -> None:
        """Passing a non-existent server_file raises VersioningError."""
        runner = FakeRunner()
        with pytest.raises(VersioningError, match="does not exist"):
            VersioningAssistant(
                Path("."),
                runner=runner,
                preflight=False,
                server_file=tmp_path / "missing.json",
            )

    def test_rerun_does_not_sync_server_file(self, tmp_path: Path) -> None:
        """Rerun should not touch the server file (no version change)."""
        server = tmp_path / "server.json"
        server.write_text('{"version": "0.1.0"}\n')

        runner = FakeRunner()
        assistant = VersioningAssistant(
            Path("."), runner=runner, preflight=False, server_file=server
        )

        assistant.rerun("0.1.0")

        # Server file content unchanged — rerun doesn't call _release
        assert '"0.1.0"' in server.read_text()
