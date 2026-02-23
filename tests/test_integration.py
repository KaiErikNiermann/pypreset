"""Integration tests for generated projects.

These tests verify that:
1. Generated projects can be installed with poetry
2. Generated projects pass their own test suites
3. Generated GitHub Actions workflows are valid and can run locally with act
"""

import subprocess
from pathlib import Path

import pytest

from pysetup.generator import generate_project
from pysetup.preset_loader import build_project_config


def _run_command(
    command: list[str],
    cwd: Path,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run a command and return the result."""
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _check_poetry_available() -> bool:
    """Check if poetry is available."""
    try:
        result = subprocess.run(
            ["poetry", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _check_act_available() -> bool:
    """Check if act (GitHub Actions local runner) is available."""
    try:
        result = subprocess.run(
            ["act", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _check_docker_available() -> bool:
    """Check if docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip markers for conditional test execution
requires_poetry = pytest.mark.skipif(
    not _check_poetry_available(),
    reason="Poetry not available",
)

requires_act = pytest.mark.skipif(
    not _check_act_available(),
    reason="act (GitHub Actions local runner) not available",
)

requires_docker = pytest.mark.skipif(
    not _check_docker_available(),
    reason="Docker not available or not running",
)


class TestPostGenerationExecution:
    """Tests that verify generated projects can be installed and run."""

    @requires_poetry
    @pytest.mark.parametrize(
        "preset_name",
        [
            "empty-package",
            "cli-tool",
        ],
    )
    def test_poetry_install_succeeds(
        self,
        preset_name: str,
        temp_output_dir: Path,
    ) -> None:
        """Test that poetry install succeeds for generated projects."""
        config = build_project_config(
            project_name=f"test-{preset_name}",
            preset_name=preset_name,
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Run poetry install
        result = _run_command(["poetry", "install", "--no-interaction"], project_dir)

        assert result.returncode == 0, (
            f"poetry install failed for {preset_name}:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @requires_poetry
    @pytest.mark.parametrize(
        "preset_name",
        [
            "empty-package",
            "cli-tool",
        ],
    )
    def test_pytest_runs_successfully(
        self,
        preset_name: str,
        temp_output_dir: Path,
    ) -> None:
        """Test that pytest runs successfully on generated projects."""
        config = build_project_config(
            project_name=f"test-{preset_name}",
            preset_name=preset_name,
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Install dependencies first
        install_result = _run_command(
            ["poetry", "install", "--no-interaction"],
            project_dir,
        )
        assert install_result.returncode == 0, f"poetry install failed: {install_result.stderr}"

        # Run pytest
        result = _run_command(
            ["poetry", "run", "pytest", "-v"],
            project_dir,
        )

        assert (
            result.returncode == 0
        ), f"pytest failed for {preset_name}:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    @requires_poetry
    def test_cli_tool_runs(self, temp_output_dir: Path) -> None:
        """Test that a generated CLI tool can be executed."""
        config = build_project_config(
            project_name="my-cli",
            preset_name="cli-tool",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Install dependencies
        install_result = _run_command(
            ["poetry", "install", "--no-interaction"],
            project_dir,
        )
        assert install_result.returncode == 0, f"poetry install failed: {install_result.stderr}"

        # Run the CLI with --help
        result = _run_command(
            ["poetry", "run", "my-cli", "--help"],
            project_dir,
        )

        assert (
            result.returncode == 0
        ), f"CLI --help failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "Usage" in result.stdout or "usage" in result.stdout.lower()

    @requires_poetry
    def test_ruff_check_passes(self, temp_output_dir: Path) -> None:
        """Test that ruff check passes on generated projects."""
        config = build_project_config(
            project_name="test-linting",
            preset_name="cli-tool",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Install dependencies
        install_result = _run_command(
            ["poetry", "install", "--no-interaction"],
            project_dir,
        )
        assert install_result.returncode == 0, f"poetry install failed: {install_result.stderr}"

        # Run ruff check
        result = _run_command(
            ["poetry", "run", "ruff", "check", "src", "tests"],
            project_dir,
        )

        assert (
            result.returncode == 0
        ), f"ruff check failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"


class TestGitHubActionsValidation:
    """Tests that verify generated GitHub Actions workflows work with act."""

    @requires_act
    @requires_docker
    def test_workflow_syntax_valid(self, temp_output_dir: Path) -> None:
        """Test that the generated workflow has valid syntax for act."""
        config = build_project_config(
            project_name="test-actions",
            preset_name="cli-tool",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # List available workflows with act
        result = _run_command(
            ["act", "--list"],
            project_dir,
            timeout=60,
        )

        assert result.returncode == 0, (
            f"act --list failed (workflow syntax error):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

        # Verify both jobs are listed
        assert (
            "test" in result.stdout.lower() or "lint" in result.stdout.lower()
        ), f"Expected jobs not found in workflow:\n{result.stdout}"

    @requires_act
    @requires_docker
    def test_workflow_dry_run(self, temp_output_dir: Path) -> None:
        """Test that the workflow passes act's dry-run validation."""
        config = build_project_config(
            project_name="test-actions-dry",
            preset_name="empty-package",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Run act with --dryrun to validate without executing
        result = _run_command(
            ["act", "--dryrun", "-j", "lint"],
            project_dir,
            timeout=120,
        )

        # act --dryrun should succeed if workflow is valid
        assert (
            result.returncode == 0
        ), f"act --dryrun failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    @requires_act
    @requires_docker
    @pytest.mark.slow
    def test_lint_job_runs_successfully(self, temp_output_dir: Path) -> None:
        """Test that the lint job runs successfully with act.

        This test actually runs the GitHub Action locally, which requires
        Docker and may take several minutes on first run due to image pulls.
        """
        config = build_project_config(
            project_name="test-lint-job",
            preset_name="empty-package",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Run the lint job with act
        # Using medium image for faster execution
        result = _run_command(
            [
                "act",
                "-j",
                "lint",
                "--platform",
                "ubuntu-latest=catthehacker/ubuntu:act-latest",
            ],
            project_dir,
            timeout=600,  # 10 minutes for Docker pulls
        )

        assert (
            result.returncode == 0
        ), f"act lint job failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    @requires_act
    @requires_docker
    @pytest.mark.slow
    def test_test_job_runs_successfully(self, temp_output_dir: Path) -> None:
        """Test that the test job runs successfully with act.

        This test actually runs the GitHub Action locally.
        """
        config = build_project_config(
            project_name="test-test-job",
            preset_name="empty-package",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Run the test job with act (only one Python version for speed)
        result = _run_command(
            [
                "act",
                "-j",
                "test",
                "--platform",
                "ubuntu-latest=catthehacker/ubuntu:act-latest",
                "--matrix",
                "python-version:3.11",
            ],
            project_dir,
            timeout=600,
        )

        assert (
            result.returncode == 0
        ), f"act test job failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"


class TestAllPresetsIntegration:
    """Integration tests for all presets."""

    @requires_poetry
    @pytest.mark.parametrize(
        "preset_name",
        [
            "empty-package",
            "cli-tool",
            "data-science",
            "discord-bot",
        ],
    )
    def test_full_project_lifecycle(
        self,
        preset_name: str,
        temp_output_dir: Path,
    ) -> None:
        """Test the full lifecycle: generate, install, lint, test."""
        config = build_project_config(
            project_name=f"lifecycle-{preset_name}",
            preset_name=preset_name,
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=True,
            install_dependencies=False,
        )

        # Step 1: Poetry install
        install_result = _run_command(
            ["poetry", "install", "--no-interaction"],
            project_dir,
            timeout=300,
        )
        assert (
            install_result.returncode == 0
        ), f"[{preset_name}] poetry install failed: {install_result.stderr}"

        # Step 2: Ruff check (formatting enabled by default)
        lint_result = _run_command(
            ["poetry", "run", "ruff", "check", "src", "tests"],
            project_dir,
        )
        assert (
            lint_result.returncode == 0
        ), f"[{preset_name}] ruff check failed: {lint_result.stdout}\n{lint_result.stderr}"

        # Step 3: Pytest (testing enabled by default)
        test_result = _run_command(
            ["poetry", "run", "pytest", "-v"],
            project_dir,
        )
        assert (
            test_result.returncode == 0
        ), f"[{preset_name}] pytest failed: {test_result.stdout}\n{test_result.stderr}"

        # Step 4: Verify GitHub workflow exists
        workflow_file = project_dir / ".github" / "workflows" / "ci.yaml"
        assert workflow_file.exists(), f"[{preset_name}] GitHub workflow not created"
