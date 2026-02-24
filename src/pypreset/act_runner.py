"""Proxy for the `act` GitHub Actions local runner.

Handles detection, installation guidance, and workflow verification
by delegating to the `act` CLI with sensible defaults.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Install instructions by platform / distro
_INSTALL_COMMANDS: dict[str, list[str]] = {
    "arch": ["sudo", "pacman", "-S", "--noconfirm", "act"],
    "fedora": ["sudo", "dnf", "install", "-y", "act-cli"],
    "ubuntu": ["sudo", "apt-get", "install", "-y", "act"],
    "debian": ["sudo", "apt-get", "install", "-y", "act"],
    "linuxbrew": ["brew", "install", "act"],
    "homebrew_macos": ["brew", "install", "act"],
}

_INSTALL_URL = "https://nektosact.com/installation/index.html"


class ActError(Exception):
    """Raised when an act operation fails."""


@dataclass
class ActCheckResult:
    """Result of checking whether act is available."""

    installed: bool
    version: str | None = None
    error: str | None = None


@dataclass
class ActRunResult:
    """Result of running act on a workflow."""

    success: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1


@dataclass
class ActInstallResult:
    """Result of attempting to install act."""

    success: bool
    method: str = ""
    message: str = ""


@dataclass
class WorkflowVerifyResult:
    """Complete result of a workflow verification."""

    act_available: bool
    act_version: str | None = None
    workflow_path: str = ""
    runs: list[ActRunResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_act() -> ActCheckResult:
    """Check if act is installed and return version info.

    Performs a meta-check: if `act --version` fails, verifies whether
    the binary truly isn't on PATH vs some other issue.
    """
    act_path = shutil.which("act")
    if act_path is None:
        return ActCheckResult(
            installed=False,
            error="act is not installed or not on PATH",
        )

    try:
        result = subprocess.run(
            ["act", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return ActCheckResult(installed=True, version=version)

        # Binary exists but --version failed — something is wrong
        return ActCheckResult(
            installed=False,
            error=f"act binary found at {act_path} but --version failed: {result.stderr.strip()}",
        )
    except subprocess.TimeoutExpired:
        return ActCheckResult(
            installed=False,
            error=f"act binary found at {act_path} but timed out on --version",
        )
    except OSError as e:
        return ActCheckResult(
            installed=False,
            error=f"Failed to execute act at {act_path}: {e}",
        )


def _detect_linux_distro() -> str | None:
    """Detect the Linux distribution family."""
    try:
        os_release = Path("/etc/os-release").read_text()
    except FileNotFoundError:
        return None

    os_release_lower = os_release.lower()
    if "arch" in os_release_lower:
        return "arch"
    if "fedora" in os_release_lower or "rhel" in os_release_lower:
        return "fedora"
    if "ubuntu" in os_release_lower:
        return "ubuntu"
    if "debian" in os_release_lower:
        return "debian"
    return None


def get_install_suggestion() -> tuple[str, list[str] | None]:
    """Return a human-readable install suggestion and optional command.

    Returns:
        Tuple of (message, command_or_None).
    """
    system = platform.system().lower()

    if system == "darwin":
        if shutil.which("brew"):
            return (
                "Install with Homebrew: brew install act",
                _INSTALL_COMMANDS["homebrew_macos"],
            )
        return (
            f"Install act from: {_INSTALL_URL}",
            None,
        )

    if system == "linux":
        distro = _detect_linux_distro()
        if distro and distro in _INSTALL_COMMANDS:
            cmd = _INSTALL_COMMANDS[distro]
            return (
                f"Install for {distro}: {' '.join(cmd)}",
                cmd,
            )
        # Fallback: try linuxbrew if available
        if shutil.which("brew"):
            return (
                "Install with Homebrew: brew install act",
                _INSTALL_COMMANDS["linuxbrew"],
            )
        return (
            f"Install act from: {_INSTALL_URL}",
            None,
        )

    # Windows or unknown
    return (
        f"Install act from: {_INSTALL_URL}",
        None,
    )


def install_act() -> ActInstallResult:
    """Attempt to install act automatically on supported systems."""
    suggestion, command = get_install_suggestion()

    if command is None:
        return ActInstallResult(
            success=False,
            method="manual",
            message=f"Automatic install not supported on this system. {suggestion}",
        )

    logger.info("Attempting to install act: %s", " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            # Verify the installation worked
            verify = check_act()
            if verify.installed:
                return ActInstallResult(
                    success=True,
                    method=" ".join(command),
                    message=f"act installed successfully ({verify.version})",
                )
            return ActInstallResult(
                success=False,
                method=" ".join(command),
                message="Install command succeeded but act still not found on PATH",
            )

        return ActInstallResult(
            success=False,
            method=" ".join(command),
            message=f"Install failed (exit {result.returncode}): {result.stderr.strip()}",
        )
    except subprocess.TimeoutExpired:
        return ActInstallResult(
            success=False,
            method=" ".join(command),
            message="Install command timed out",
        )
    except OSError as e:
        return ActInstallResult(
            success=False,
            method=" ".join(command),
            message=f"Failed to run install command: {e}",
        )


def _build_act_command(
    *,
    workflow_file: Path | None = None,
    job: str | None = None,
    event: str = "push",
    dry_run: bool = False,
    list_jobs: bool = False,
    platform_map: str | None = None,
    extra_flags: list[str] | None = None,
) -> list[str]:
    """Build the act command with sensible defaults."""
    cmd = ["act"]

    if list_jobs:
        cmd.append("--list")
    elif dry_run:
        cmd.append("--dryrun")

    if workflow_file is not None:
        cmd.extend(["-W", str(workflow_file)])

    if job:
        cmd.extend(["-j", job])

    if not list_jobs:
        cmd.append(event)

    if platform_map:
        cmd.extend(["--platform", platform_map])

    if extra_flags:
        cmd.extend(extra_flags)

    return cmd


def run_act(
    *,
    project_dir: Path,
    workflow_file: Path | None = None,
    job: str | None = None,
    event: str = "push",
    dry_run: bool = False,
    list_jobs: bool = False,
    platform_map: str | None = None,
    extra_flags: list[str] | None = None,
    timeout: int = 600,
) -> ActRunResult:
    """Run act with the given options.

    Args:
        project_dir: The project root (cwd for act).
        workflow_file: Specific workflow file to run (relative to project_dir).
        job: Specific job to run.
        event: GitHub event to simulate (default: push).
        dry_run: Run in dry-run mode (validate without executing).
        list_jobs: Just list available jobs.
        platform_map: Platform mapping (e.g. 'ubuntu-latest=catthehacker/ubuntu:act-latest').
        extra_flags: Additional flags to pass to act.
        timeout: Command timeout in seconds.

    Returns:
        ActRunResult with command output.
    """
    cmd = _build_act_command(
        workflow_file=workflow_file,
        job=job,
        event=event,
        dry_run=dry_run,
        list_jobs=list_jobs,
        platform_map=platform_map,
        extra_flags=extra_flags,
    )

    logger.info("Running: %s (cwd=%s)", " ".join(cmd), project_dir)

    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ActRunResult(
            success=result.returncode == 0,
            command=cmd,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return ActRunResult(
            success=False,
            command=cmd,
            stderr=f"Command timed out after {timeout}s",
            return_code=-1,
        )
    except OSError as e:
        return ActRunResult(
            success=False,
            command=cmd,
            stderr=f"Failed to execute: {e}",
            return_code=-1,
        )


def verify_workflow(
    *,
    project_dir: Path,
    workflow_file: Path | None = None,
    job: str | None = None,
    event: str = "push",
    dry_run: bool = True,
    platform_map: str | None = None,
    extra_flags: list[str] | None = None,
    timeout: int = 600,
    auto_install: bool = False,
) -> WorkflowVerifyResult:
    """Verify a GitHub Actions workflow using act.

    This is the main entry point. It:
    1. Checks if act is installed (with meta-check on failure)
    2. Optionally attempts auto-install
    3. Lists workflow jobs for info
    4. Runs the workflow in dry-run or full mode
    5. Surfaces all act output back to the caller

    Args:
        project_dir: Path to the project root.
        workflow_file: Specific workflow file (relative to project). If None,
            act will discover workflows in .github/workflows/.
        job: Specific job name to run. If None, runs all jobs.
        event: GitHub event to simulate.
        dry_run: If True, validate without executing containers.
        platform_map: Platform mapping for act.
        extra_flags: Additional flags forwarded to act.
        timeout: Timeout in seconds for act commands.
        auto_install: Attempt automatic installation if act is missing.

    Returns:
        WorkflowVerifyResult with all details.
    """
    result = WorkflowVerifyResult(act_available=False)

    if workflow_file is not None:
        result.workflow_path = str(workflow_file)

    # Step 1: Check act availability
    check = check_act()
    if not check.installed:
        if auto_install:
            install_result = install_act()
            if install_result.success:
                check = check_act()
            else:
                result.errors.append(f"act not installed: {check.error}")
                result.errors.append(f"Auto-install failed: {install_result.message}")
                suggestion, _ = get_install_suggestion()
                result.warnings.append(suggestion)
                return result

        if not check.installed:
            result.errors.append(f"act not installed: {check.error}")
            suggestion, _ = get_install_suggestion()
            result.warnings.append(suggestion)
            result.warnings.append(
                "WARNING: Do not assume act is installed. "
                "Workflow verification requires act to be present."
            )
            return result

    result.act_available = True
    result.act_version = check.version

    # Step 2: Verify workflow directory exists
    workflows_dir = project_dir / ".github" / "workflows"
    if workflow_file is None and not workflows_dir.exists():
        result.errors.append(f"No .github/workflows/ directory found in {project_dir}")
        return result

    if workflow_file is not None:
        # Resolve relative to project_dir
        full_path = project_dir / workflow_file
        if not full_path.exists():
            result.errors.append(f"Workflow file not found: {full_path}")
            return result

    # Step 3: List available jobs (informational)
    list_run = run_act(
        project_dir=project_dir,
        workflow_file=workflow_file,
        list_jobs=True,
        timeout=30,
    )
    result.runs.append(list_run)

    if not list_run.success:
        result.errors.append(f"Failed to list workflow jobs: {list_run.stderr.strip()}")
        return result

    # Step 4: Run verification
    verify_run = run_act(
        project_dir=project_dir,
        workflow_file=workflow_file,
        job=job,
        event=event,
        dry_run=dry_run,
        platform_map=platform_map,
        extra_flags=extra_flags,
        timeout=timeout,
    )
    result.runs.append(verify_run)

    if not verify_run.success:
        result.errors.append(f"Workflow verification failed (exit {verify_run.return_code})")

    return result
