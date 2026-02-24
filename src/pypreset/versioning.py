"""Versioning assistance utilities."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

ToolName = Literal["git", "poetry", "gh"]


class VersioningError(Exception):
    """Error raised for versioning failures."""


@dataclass(frozen=True)
class CommandFailure(VersioningError):
    """Error raised when a command fails."""

    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str

    def __str__(self) -> str:
        command_str = " ".join(self.command)
        parts = [f"Command failed: {command_str}"]
        if self.returncode is not None:
            parts.append(f"Exit code: {self.returncode}")
        if self.stdout.strip():
            parts.append(f"Stdout: {self.stdout.strip()}")
        if self.stderr.strip():
            parts.append(f"Stderr: {self.stderr.strip()}")
        return "\n".join(parts)


class CommandRunner(Protocol):
    """Protocol for running shell commands."""

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a command and return the completed process."""
        ...


class SubprocessRunner:
    """Subprocess-backed command runner."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a command with subprocess."""
        try:
            return subprocess.run(
                args,
                cwd=self.cwd,
                text=True,
                capture_output=True,
                check=check,
            )
        except subprocess.CalledProcessError as exc:
            raise CommandFailure(
                command=args,
                returncode=exc.returncode,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            ) from exc
        except FileNotFoundError as exc:
            raise CommandFailure(
                command=args,
                returncode=None,
                stdout="",
                stderr=f"{args[0]} not found",
            ) from exc


def _normalize_prefixed_value(value: str, key: Literal["bump", "version"]) -> str:
    normalized = value.strip()
    prefix = f"{key}="
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix) :].strip()
    if not normalized:
        raise VersioningError(f"{key} cannot be empty")
    return normalized


def _check_required_tools(tools: list[ToolName]) -> None:
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        joined = ", ".join(missing)
        raise VersioningError(f"Missing required tools: {joined}")


def _tag_name(version: str) -> str:
    return f"v{version}"


def sync_server_file(server_file: Path, version: str) -> int:
    """Update all ``"version": "..."`` values in a JSON server file.

    Reads the file as text and performs a regex replacement so the rest of the
    file (formatting, comments, trailing newline) is preserved exactly.

    Returns the number of replacements made.
    """
    import re

    text = server_file.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'("version"\s*:\s*)"[^"]*"',
        rf'\g<1>"{version}"',
        text,
    )
    if count > 0:
        server_file.write_text(new_text, encoding="utf-8")
        logger.info("Synced %d version field(s) in %s to %s", count, server_file, version)
    return count


class VersioningAssistant:
    """Implements versioning workflows inspired by the project's Justfile."""

    def __init__(
        self,
        project_dir: Path,
        runner: CommandRunner | None = None,
        *,
        preflight: bool = True,
        server_file: Path | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.runner = runner or SubprocessRunner(project_dir)
        self.server_file = server_file
        if preflight:
            self._preflight()
        if server_file and not server_file.exists():
            raise VersioningError(f"Server file '{server_file}' does not exist")

    def release(self, bump: str) -> str:
        """Bump version, commit, tag, push, and create a GitHub release."""
        normalized = _normalize_prefixed_value(bump, "bump")
        self._run_checked(["poetry", "version", normalized])
        version = self._read_version()
        self._release(version)
        return version

    def release_version(self, version: str) -> str:
        """Use an explicit version, then commit, tag, push, and release."""
        normalized = _normalize_prefixed_value(version, "version")
        self._run_checked(["poetry", "version", normalized])
        self._release(normalized)
        return normalized

    def rerun(self, version: str) -> str:
        """Re-tag and push an existing version."""
        normalized = _normalize_prefixed_value(version, "version")
        tag = _tag_name(normalized)
        self._run_checked(["git", "push"])
        self._run_allowed_failure(["git", "tag", "-d", tag])
        self._run_allowed_failure(["git", "push", "--delete", "origin", tag])
        self._run_checked(["git", "tag", tag])
        self._run_checked(["git", "push", "origin", tag])
        return normalized

    def rerelease(self, version: str) -> str:
        """Delete and recreate a GitHub release for a version."""
        normalized = _normalize_prefixed_value(version, "version")
        tag = _tag_name(normalized)
        self._run_allowed_failure(["gh", "release", "delete", tag, "-y"])
        self.rerun(normalized)
        self._run_checked(["gh", "release", "create", tag, "--title", tag, "--generate-notes"])
        return normalized

    def _preflight(self) -> None:
        if not self.project_dir.exists():
            raise VersioningError(f"Directory '{self.project_dir}' does not exist")
        _check_required_tools(["poetry", "git", "gh"])

    def _read_version(self) -> str:
        result = self.runner.run(["poetry", "version", "--short"])
        version = result.stdout.strip()
        if not version:
            raise VersioningError("Unable to read version from poetry")
        return version

    def _release(self, version: str) -> None:
        tag = _tag_name(version)
        self._sync_server_file(version)
        self._run_checked(["git", "add", "pyproject.toml"])
        self._run_checked(["git", "add", "-f", "poetry.lock"])
        if self.server_file:
            self._run_checked(["git", "add", str(self.server_file)])
        self._run_checked(["git", "commit", "-m", f"chore(release): {tag}"])
        self._run_checked(["git", "push"])
        self._run_checked(["git", "tag", tag])
        self._run_checked(["git", "push", "origin", tag])
        self._run_checked(["gh", "release", "create", tag, "--title", tag, "--generate-notes"])

    def _sync_server_file(self, version: str) -> None:
        """Sync version in the MCP server file if configured."""
        if not self.server_file:
            return
        count = sync_server_file(self.server_file, version)
        if count == 0:
            logger.warning("No version fields found in %s — file left unchanged", self.server_file)

    def _run_checked(self, args: list[str]) -> None:
        self.runner.run(args, check=True)

    def _run_allowed_failure(self, args: list[str]) -> None:
        self.runner.run(args, check=False)
