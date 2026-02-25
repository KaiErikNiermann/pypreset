"""Proxy for the ``migrate-to-uv`` CLI tool.

``migrate-to-uv`` (https://github.com/mkniewallner/migrate-to-uv) migrates
Python projects to uv from other package managers (Poetry, Pipenv, pip-tools,
pip).  This module wraps the upstream CLI and surfaces its output/errors
through pypreset's own interface.

MIT License — Copyright (c) 2025 Mathieu Kniewallner.
See THIRD_PARTY_NOTICES.md for the full license text.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

PackageManagerSource = Literal["poetry", "pipenv", "pip-tools", "pip"]
DependencyGroupsStrategy = Literal[
    "set-default-groups-all",
    "set-default-groups",
    "include-in-dev",
    "keep-existing",
    "merge-into-dev",
]
BuildBackend = Literal["hatch", "uv"]


class MigrationError(Exception):
    """Error raised when a migration operation fails."""


@dataclass(frozen=True)
class MigrationCommandFailure(MigrationError):
    """Error raised when the migrate-to-uv command fails."""

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


@dataclass(frozen=True)
class MigrationResult:
    """Result of a migrate-to-uv invocation."""

    success: bool
    command: list[str]
    stdout: str
    stderr: str
    return_code: int | None
    dry_run: bool = False


@dataclass
class MigrationOptions:
    """Options for the migrate-to-uv command."""

    project_dir: Path = field(default_factory=lambda: Path("."))
    dry_run: bool = False
    skip_lock: bool = False
    skip_uv_checks: bool = False
    ignore_locked_versions: bool = False
    replace_project_section: bool = False
    keep_current_build_backend: bool = False
    keep_current_data: bool = False
    ignore_errors: bool = False
    package_manager: PackageManagerSource | None = None
    dependency_groups_strategy: DependencyGroupsStrategy | None = None
    build_backend: BuildBackend | None = None


def check_migrate_to_uv() -> tuple[bool, str | None]:
    """Check whether ``migrate-to-uv`` is available on PATH.

    Returns:
        Tuple of (is_available, version_string_or_None).
    """
    path = shutil.which("migrate-to-uv")
    if path is None:
        return False, None

    try:
        result = subprocess.run(
            ["migrate-to-uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return True, version
    except FileNotFoundError:
        return False, None


def _build_args(opts: MigrationOptions) -> list[str]:
    """Build the CLI argument list from *opts*."""
    args: list[str] = ["migrate-to-uv"]

    if opts.dry_run:
        args.append("--dry-run")
    if opts.skip_lock:
        args.append("--skip-lock")
    if opts.skip_uv_checks:
        args.append("--skip-uv-checks")
    if opts.ignore_locked_versions:
        args.append("--ignore-locked-versions")
    if opts.replace_project_section:
        args.append("--replace-project-section")
    if opts.keep_current_build_backend:
        args.append("--keep-current-build-backend")
    if opts.keep_current_data:
        args.append("--keep-current-data")
    if opts.ignore_errors:
        args.append("--ignore-errors")
    if opts.package_manager is not None:
        args.extend(["--package-manager", opts.package_manager])
    if opts.dependency_groups_strategy is not None:
        args.extend(["--dependency-groups-strategy", opts.dependency_groups_strategy])
    if opts.build_backend is not None:
        args.extend(["--build-backend", opts.build_backend])

    args.append(str(opts.project_dir))
    return args


def migrate_to_uv(opts: MigrationOptions | None = None) -> MigrationResult:
    """Run ``migrate-to-uv`` with the given options.

    Raises:
        MigrationError: If ``migrate-to-uv`` is not installed.
        MigrationCommandFailure: If the command exits with a non-zero status
            and ``ignore_errors`` is not set.
    """
    if opts is None:
        opts = MigrationOptions()

    available, _ = check_migrate_to_uv()
    if not available:
        raise MigrationError(
            "migrate-to-uv is not installed. "
            "Install it with: pip install migrate-to-uv  (or: uvx migrate-to-uv)"
        )

    args = _build_args(opts)
    logger.debug("Running: %s", " ".join(args))

    try:
        result = subprocess.run(
            args,
            cwd=str(opts.project_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MigrationError("migrate-to-uv not found on PATH") from exc

    if result.returncode != 0 and not opts.ignore_errors:
        raise MigrationCommandFailure(
            command=args,
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    return MigrationResult(
        success=result.returncode == 0,
        command=args,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        return_code=result.returncode,
        dry_run=opts.dry_run,
    )
