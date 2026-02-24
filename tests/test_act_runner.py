"""Tests for the act runner proxy module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pypreset.act_runner import (
    ActCheckResult,
    ActRunResult,
    check_act,
    get_install_suggestion,
    install_act,
    run_act,
    verify_workflow,
)


class TestCheckAct:
    """Tests for check_act()."""

    def test_act_not_on_path(self) -> None:
        with patch("pypreset.act_runner.shutil.which", return_value=None):
            result = check_act()
        assert result.installed is False
        assert "not installed" in (result.error or "")

    def test_act_installed_and_working(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "act version 0.2.60"
        with (
            patch("pypreset.act_runner.shutil.which", return_value="/usr/bin/act"),
            patch("pypreset.act_runner.subprocess.run", return_value=mock_result),
        ):
            result = check_act()
        assert result.installed is True
        assert result.version == "act version 0.2.60"

    def test_act_binary_exists_but_fails(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"
        with (
            patch("pypreset.act_runner.shutil.which", return_value="/usr/bin/act"),
            patch("pypreset.act_runner.subprocess.run", return_value=mock_result),
        ):
            result = check_act()
        assert result.installed is False
        assert "failed" in (result.error or "").lower()

    def test_act_binary_timeout(self) -> None:
        import subprocess

        with (
            patch("pypreset.act_runner.shutil.which", return_value="/usr/bin/act"),
            patch(
                "pypreset.act_runner.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="act", timeout=10),
            ),
        ):
            result = check_act()
        assert result.installed is False
        assert "timed out" in (result.error or "")

    def test_act_binary_os_error(self) -> None:
        with (
            patch("pypreset.act_runner.shutil.which", return_value="/usr/bin/act"),
            patch(
                "pypreset.act_runner.subprocess.run",
                side_effect=OSError("Permission denied"),
            ),
        ):
            result = check_act()
        assert result.installed is False
        assert "Permission denied" in (result.error or "")


class TestGetInstallSuggestion:
    """Tests for get_install_suggestion()."""

    def test_linux_arch(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Linux"),
            patch(
                "pypreset.act_runner.Path.read_text",
                return_value='ID=arch\nNAME="Arch Linux"',
            ),
        ):
            msg, cmd = get_install_suggestion()
        assert "arch" in msg.lower()
        assert cmd is not None
        assert "pacman" in cmd

    def test_linux_ubuntu(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Linux"),
            patch(
                "pypreset.act_runner.Path.read_text",
                return_value='ID=ubuntu\nNAME="Ubuntu"',
            ),
        ):
            suggestion, cmd = get_install_suggestion()
        assert cmd is not None
        assert "apt-get" in cmd
        assert suggestion  # non-empty

    def test_linux_fedora(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Linux"),
            patch(
                "pypreset.act_runner.Path.read_text",
                return_value='ID=fedora\nNAME="Fedora"',
            ),
        ):
            suggestion, cmd = get_install_suggestion()
        assert cmd is not None
        assert "dnf" in cmd
        assert suggestion  # non-empty

    def test_linux_unknown_with_brew(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Linux"),
            patch(
                "pypreset.act_runner.Path.read_text",
                return_value='ID=void\nNAME="Void Linux"',
            ),
            patch(
                "pypreset.act_runner.shutil.which", return_value="/home/user/.linuxbrew/bin/brew"
            ),
        ):
            msg, cmd = get_install_suggestion()
        assert "brew" in msg.lower()
        assert cmd is not None

    def test_linux_unknown_no_brew(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Linux"),
            patch(
                "pypreset.act_runner.Path.read_text",
                return_value='ID=void\nNAME="Void Linux"',
            ),
            patch("pypreset.act_runner.shutil.which", return_value=None),
        ):
            msg, cmd = get_install_suggestion()
        assert "nektosact.com" in msg
        assert cmd is None

    def test_macos_with_brew(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Darwin"),
            patch("pypreset.act_runner.shutil.which", return_value="/opt/homebrew/bin/brew"),
        ):
            msg, cmd = get_install_suggestion()
        assert "brew" in msg.lower()
        assert cmd is not None

    def test_macos_no_brew(self) -> None:
        with (
            patch("pypreset.act_runner.platform.system", return_value="Darwin"),
            patch("pypreset.act_runner.shutil.which", return_value=None),
        ):
            msg, cmd = get_install_suggestion()
        assert "nektosact.com" in msg
        assert cmd is None

    def test_windows(self) -> None:
        with patch("pypreset.act_runner.platform.system", return_value="Windows"):
            msg, cmd = get_install_suggestion()
        assert "nektosact.com" in msg
        assert cmd is None


class TestInstallAct:
    """Tests for install_act()."""

    def test_no_auto_command_available(self) -> None:
        with patch(
            "pypreset.act_runner.get_install_suggestion",
            return_value=("Install from website", None),
        ):
            result = install_act()
        assert result.success is False
        assert result.method == "manual"

    def test_install_succeeds(self) -> None:
        mock_install = MagicMock()
        mock_install.returncode = 0

        with (
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install with pacman", ["sudo", "pacman", "-S", "act"]),
            ),
            patch("pypreset.act_runner.subprocess.run", return_value=mock_install),
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
        ):
            result = install_act()
        assert result.success is True

    def test_install_command_fails(self) -> None:
        mock_install = MagicMock()
        mock_install.returncode = 1
        mock_install.stderr = "package not found"

        with (
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install with pacman", ["sudo", "pacman", "-S", "act"]),
            ),
            patch("pypreset.act_runner.subprocess.run", return_value=mock_install),
        ):
            result = install_act()
        assert result.success is False
        assert "package not found" in result.message


class TestRunAct:
    """Tests for run_act()."""

    def test_successful_list(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Stage  Job ID  Job name\n0      lint    lint\n0      test    test"
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(project_dir=tmp_path, list_jobs=True)

        assert result.success is True
        assert "lint" in result.stdout

    def test_dry_run(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "dry run complete"
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(project_dir=tmp_path, dry_run=True)

        assert result.success is True
        assert "--dryrun" in result.command

    def test_with_workflow_file(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(
                project_dir=tmp_path,
                workflow_file=Path(".github/workflows/ci.yaml"),
                dry_run=True,
            )

        assert "-W" in result.command
        assert ".github/workflows/ci.yaml" in result.command

    def test_with_job_filter(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(project_dir=tmp_path, job="lint", dry_run=True)

        assert "-j" in result.command
        assert "lint" in result.command

    def test_with_extra_flags(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(
                project_dir=tmp_path,
                dry_run=True,
                extra_flags=["--secret", "FOO=bar"],
            )

        assert "--secret" in result.command
        assert "FOO=bar" in result.command

    def test_timeout(self, tmp_path: Path) -> None:
        import subprocess

        with patch(
            "pypreset.act_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="act", timeout=5),
        ):
            result = run_act(project_dir=tmp_path, dry_run=True, timeout=5)

        assert result.success is False
        assert "timed out" in result.stderr.lower()

    def test_os_error(self, tmp_path: Path) -> None:
        with patch(
            "pypreset.act_runner.subprocess.run",
            side_effect=OSError("No such file"),
        ):
            result = run_act(project_dir=tmp_path, dry_run=True)

        assert result.success is False
        assert "No such file" in result.stderr

    def test_with_platform_map(self, tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pypreset.act_runner.subprocess.run", return_value=mock_result):
            result = run_act(
                project_dir=tmp_path,
                dry_run=True,
                platform_map="ubuntu-latest=catthehacker/ubuntu:act-latest",
            )

        assert "--platform" in result.command


class TestVerifyWorkflow:
    """Tests for verify_workflow() — the main orchestration function."""

    def test_act_not_installed_no_auto_install(self, tmp_path: Path) -> None:
        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=False, error="not on PATH"),
            ),
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install from website", None),
            ),
        ):
            result = verify_workflow(project_dir=tmp_path)

        assert result.act_available is False
        assert any("not installed" in e for e in result.errors)
        assert any("WARNING" in w for w in result.warnings)

    def test_act_not_installed_auto_install_succeeds(self, tmp_path: Path) -> None:
        # Set up workflows dir so verification can proceed
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yaml").write_text(
            "on: push\njobs:\n  test:\n    runs-on: ubuntu-latest"
        )

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="lint\ntest", return_code=0
        )
        verify_mock = ActRunResult(
            success=True, command=["act", "--dryrun", "push"], stdout="ok", return_code=0
        )

        from pypreset.act_runner import ActInstallResult

        with (
            patch(
                "pypreset.act_runner.check_act",
                side_effect=[
                    ActCheckResult(installed=False, error="not found"),
                    ActCheckResult(installed=True, version="act 0.2.60"),
                ],
            ),
            patch(
                "pypreset.act_runner.install_act",
                return_value=ActInstallResult(success=True, message="installed"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = verify_workflow(
                project_dir=tmp_path,
                auto_install=True,
            )

        assert result.act_available is True
        assert len(result.errors) == 0

    def test_act_not_installed_auto_install_fails(self, tmp_path: Path) -> None:
        from pypreset.act_runner import ActInstallResult

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=False, error="not found"),
            ),
            patch(
                "pypreset.act_runner.install_act",
                return_value=ActInstallResult(success=False, message="dnf failed"),
            ),
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install from website", None),
            ),
        ):
            result = verify_workflow(
                project_dir=tmp_path,
                auto_install=True,
            )

        assert result.act_available is False
        assert any("Auto-install failed" in e for e in result.errors)

    def test_no_workflows_directory(self, tmp_path: Path) -> None:
        with patch(
            "pypreset.act_runner.check_act",
            return_value=ActCheckResult(installed=True, version="act 0.2.60"),
        ):
            result = verify_workflow(project_dir=tmp_path)

        assert any(".github/workflows" in e for e in result.errors)

    def test_workflow_file_not_found(self, tmp_path: Path) -> None:
        with patch(
            "pypreset.act_runner.check_act",
            return_value=ActCheckResult(installed=True, version="act 0.2.60"),
        ):
            result = verify_workflow(
                project_dir=tmp_path,
                workflow_file=Path(".github/workflows/nonexistent.yaml"),
            )

        assert any("not found" in e for e in result.errors)

    def test_successful_verification(self, tmp_path: Path) -> None:
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yaml").write_text("on: push")

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="lint\ntest", return_code=0
        )
        verify_mock = ActRunResult(
            success=True, command=["act", "--dryrun", "push"], stdout="ok", return_code=0
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = verify_workflow(project_dir=tmp_path)

        assert result.act_available is True
        assert len(result.errors) == 0
        assert len(result.runs) == 2

    def test_list_fails_stops_early(self, tmp_path: Path) -> None:
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yaml").write_text("on: push")

        list_mock = ActRunResult(
            success=False,
            command=["act", "--list"],
            stderr="invalid yaml",
            return_code=1,
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                return_value=list_mock,
            ),
        ):
            result = verify_workflow(project_dir=tmp_path)

        assert any("Failed to list" in e for e in result.errors)
        # Should have only the list run, not the verify run
        assert len(result.runs) == 1

    def test_verification_fails(self, tmp_path: Path) -> None:
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yaml").write_text("on: push")

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="lint", return_code=0
        )
        verify_mock = ActRunResult(
            success=False,
            command=["act", "--dryrun", "push"],
            stderr="step failed",
            return_code=1,
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = verify_workflow(project_dir=tmp_path)

        assert any("verification failed" in e.lower() for e in result.errors)

    def test_specific_workflow_file(self, tmp_path: Path) -> None:
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yaml").write_text("on: push")

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="test", return_code=0
        )
        verify_mock = ActRunResult(
            success=True, command=["act", "--dryrun"], stdout="ok", return_code=0
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = verify_workflow(
                project_dir=tmp_path,
                workflow_file=Path(".github/workflows/ci.yaml"),
            )

        assert result.workflow_path == ".github/workflows/ci.yaml"
        assert len(result.errors) == 0
