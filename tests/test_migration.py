"""Tests for the migration module (migrate-to-uv proxy)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pypreset.migration import (
    MigrationCommandFailure,
    MigrationError,
    MigrationOptions,
    MigrationResult,
    _build_args,
    check_migrate_to_uv,
    migrate_to_uv,
)


class TestCheckMigrateToUv:
    """Tests for check_migrate_to_uv()."""

    def test_not_installed(self) -> None:
        with patch("pypreset.migration.shutil.which", return_value=None):
            available, version = check_migrate_to_uv()
        assert available is False
        assert version is None

    def test_installed_with_version(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "migrate-to-uv 0.11.0\n"
        mock_result.stderr = ""

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run", return_value=mock_result),
        ):
            available, version = check_migrate_to_uv()

        assert available is True
        assert version == "migrate-to-uv 0.11.0"

    def test_installed_version_in_stderr(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "migrate-to-uv 0.11.0"

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run", return_value=mock_result),
        ):
            available, version = check_migrate_to_uv()

        assert available is True
        assert version == "migrate-to-uv 0.11.0"

    def test_which_found_but_run_fails(self) -> None:
        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch(
                "pypreset.migration.subprocess.run",
                side_effect=FileNotFoundError("not found"),
            ),
        ):
            available, version = check_migrate_to_uv()

        assert available is False
        assert version is None


class TestBuildArgs:
    """Tests for _build_args()."""

    def test_defaults(self) -> None:
        opts = MigrationOptions()
        args = _build_args(opts)
        assert args == ["migrate-to-uv", "."]

    def test_all_flags(self) -> None:
        opts = MigrationOptions(
            project_dir=Path("/my/project"),
            dry_run=True,
            skip_lock=True,
            skip_uv_checks=True,
            ignore_locked_versions=True,
            replace_project_section=True,
            keep_current_build_backend=True,
            keep_current_data=True,
            ignore_errors=True,
        )
        args = _build_args(opts)
        assert "--dry-run" in args
        assert "--skip-lock" in args
        assert "--skip-uv-checks" in args
        assert "--ignore-locked-versions" in args
        assert "--replace-project-section" in args
        assert "--keep-current-build-backend" in args
        assert "--keep-current-data" in args
        assert "--ignore-errors" in args
        assert args[-1] == "/my/project"

    def test_package_manager_option(self) -> None:
        opts = MigrationOptions(package_manager="poetry")
        args = _build_args(opts)
        idx = args.index("--package-manager")
        assert args[idx + 1] == "poetry"

    def test_dependency_groups_strategy(self) -> None:
        opts = MigrationOptions(dependency_groups_strategy="merge-into-dev")
        args = _build_args(opts)
        idx = args.index("--dependency-groups-strategy")
        assert args[idx + 1] == "merge-into-dev"

    def test_build_backend(self) -> None:
        opts = MigrationOptions(build_backend="hatch")
        args = _build_args(opts)
        idx = args.index("--build-backend")
        assert args[idx + 1] == "hatch"


class TestMigrateToUv:
    """Tests for migrate_to_uv()."""

    def test_not_installed_raises(self) -> None:
        with (
            patch("pypreset.migration.shutil.which", return_value=None),
            pytest.raises(MigrationError, match="not installed"),
        ):
            migrate_to_uv()

    def test_successful_migration(self) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "Successfully migrated project from Poetry to uv!"
        mock_result.stderr = ""

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run", return_value=mock_result) as mock_run,
        ):
            # First call is for --version check, second is actual migration
            version_result = MagicMock()
            version_result.stdout = "migrate-to-uv 0.11.0"
            version_result.stderr = ""
            mock_run.side_effect = [version_result, mock_result]

            result = migrate_to_uv()

        assert isinstance(result, MigrationResult)
        assert result.success is True
        assert "Successfully migrated" in result.stdout

    def test_command_failure_raises(self) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Project is already using uv"

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run") as mock_run,
        ):
            version_result = MagicMock()
            version_result.stdout = "migrate-to-uv 0.11.0"
            version_result.stderr = ""
            mock_run.side_effect = [version_result, mock_result]

            with pytest.raises(MigrationCommandFailure) as exc_info:
                migrate_to_uv()

        assert exc_info.value.returncode == 1
        assert "already using uv" in exc_info.value.stderr

    def test_command_failure_ignored_with_flag(self) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stdout = "Partially migrated"
        mock_result.stderr = "warnings occurred"

        opts = MigrationOptions(ignore_errors=True)

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run") as mock_run,
        ):
            version_result = MagicMock()
            version_result.stdout = "migrate-to-uv 0.11.0"
            version_result.stderr = ""
            mock_run.side_effect = [version_result, mock_result]

            result = migrate_to_uv(opts)

        assert result.success is False
        assert result.return_code == 1

    def test_dry_run_flag_propagated(self) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "[project]\nname = 'my-project'"
        mock_result.stderr = ""

        opts = MigrationOptions(dry_run=True)

        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run") as mock_run,
        ):
            version_result = MagicMock()
            version_result.stdout = "migrate-to-uv 0.11.0"
            version_result.stderr = ""
            mock_run.side_effect = [version_result, mock_result]

            result = migrate_to_uv(opts)

        assert result.dry_run is True
        assert result.success is True
        # Verify --dry-run was passed to the command
        actual_call_args = mock_run.call_args_list[1][0][0]
        assert "--dry-run" in actual_call_args

    def test_file_not_found_during_run(self) -> None:
        with (
            patch("pypreset.migration.shutil.which", return_value="/usr/bin/migrate-to-uv"),
            patch("pypreset.migration.subprocess.run") as mock_run,
        ):
            version_result = MagicMock()
            version_result.stdout = "0.11.0"
            version_result.stderr = ""
            mock_run.side_effect = [version_result, FileNotFoundError("gone")]

            with pytest.raises(MigrationError, match="not found on PATH"):
                migrate_to_uv()


class TestMigrationResult:
    """Tests for the MigrationResult dataclass."""

    def test_fields(self) -> None:
        result = MigrationResult(
            success=True,
            command=["migrate-to-uv", "."],
            stdout="ok",
            stderr="",
            return_code=0,
            dry_run=False,
        )
        assert result.success is True
        assert result.command == ["migrate-to-uv", "."]
        assert result.return_code == 0


class TestMigrationCommandFailure:
    """Tests for the MigrationCommandFailure error."""

    def test_str_formatting(self) -> None:
        exc = MigrationCommandFailure(
            command=["migrate-to-uv", "--dry-run", "."],
            returncode=1,
            stdout="partial output",
            stderr="error details",
        )
        msg = str(exc)
        assert "Command failed: migrate-to-uv --dry-run ." in msg
        assert "Exit code: 1" in msg
        assert "partial output" in msg
        assert "error details" in msg

    def test_str_no_returncode(self) -> None:
        exc = MigrationCommandFailure(
            command=["migrate-to-uv"],
            returncode=None,
            stdout="",
            stderr="not found",
        )
        msg = str(exc)
        assert "Exit code" not in msg
        assert "not found" in msg

    def test_inherits_from_migration_error(self) -> None:
        exc = MigrationCommandFailure(
            command=["migrate-to-uv"],
            returncode=1,
            stdout="",
            stderr="",
        )
        assert isinstance(exc, MigrationError)
