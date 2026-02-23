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
