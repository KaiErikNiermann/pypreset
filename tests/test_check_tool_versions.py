"""Tests for the version sync guard script."""

# Import from the scripts directory
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path for import
_scripts_dir = str(Path(__file__).parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

import check_tool_versions  # noqa: E402


class TestPoetrySpecToPep440:
    """Tests for Poetry spec conversion."""

    def test_caret_major(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("^9.0.2") == ">=9.0.2,<10.0.0"

    def test_caret_major_nonzero(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("^1.1.408") == ">=1.1.408,<2.0.0"

    def test_caret_zero_major(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("^0.15.2") == ">=0.15.2,<0.16.0"

    def test_caret_zero_both(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("^0.0.3") == ">=0.0.3,<0.0.4"

    def test_tilde(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("~6.0.1") == ">=6.0.1,<6.1.0"

    def test_passthrough_gte(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440(">=1.0") == ">=1.0"

    def test_passthrough_exact(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("==2.0.0") == "==2.0.0"

    def test_whitespace_stripped(self) -> None:
        assert check_tool_versions._poetry_spec_to_pep440("  ^1.0.0  ") == ">=1.0.0,<2.0.0"


class TestExtractVersionSpec:
    """Tests for extracting version spec from dependency values."""

    def test_string_value(self) -> None:
        assert check_tool_versions._extract_version_spec("^1.0.0") == "^1.0.0"

    def test_dict_with_version(self) -> None:
        assert (
            check_tool_versions._extract_version_spec({"version": "^1.0.0", "optional": True})
            == "^1.0.0"
        )

    def test_dict_without_version(self) -> None:
        assert check_tool_versions._extract_version_spec({"optional": True}) is None

    def test_other_type(self) -> None:
        assert check_tool_versions._extract_version_spec(42) is None


class TestCheckVersions:
    """Tests for the main check_versions function."""

    def test_all_versions_match(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.group.dev.dependencies]
ruff = "^0.15.0"
"""
        )

        with patch(
            "check_tool_versions.installed_version",
            return_value="0.15.4",
        ):
            mismatches = check_tool_versions.check_versions(pyproject)

        assert mismatches == []

    def test_version_mismatch(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.group.dev.dependencies]
ruff = "^0.15.0"
"""
        )

        with patch(
            "check_tool_versions.installed_version",
            return_value="0.8.6",
        ):
            mismatches = check_tool_versions.check_versions(pyproject)

        assert len(mismatches) == 1
        assert "ruff" in mismatches[0]
        assert "0.8.6" in mismatches[0]

    def test_tool_not_installed(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.group.dev.dependencies]
ruff = "^0.15.0"
"""
        )

        with patch(
            "check_tool_versions.installed_version",
            side_effect=check_tool_versions.PackageNotFoundError("ruff"),
        ):
            mismatches = check_tool_versions.check_versions(pyproject)

        assert len(mismatches) == 1
        assert "not installed" in mismatches[0]

    def test_tool_not_in_pyproject(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.dependencies]
python = ">=3.14"
"""
        )

        mismatches = check_tool_versions.check_versions(pyproject)
        assert mismatches == []

    def test_main_and_dev_dependencies(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.dependencies]
pyright = "^1.1.408"

[tool.poetry.group.dev.dependencies]
ruff = "^0.15.2"
pytest = "^9.0.2"
"""
        )

        def mock_version(name: str) -> str:
            versions = {"pyright": "1.1.410", "ruff": "0.15.4", "pytest": "9.1.0"}
            return versions.get(name, "0.0.0")

        with patch("check_tool_versions.installed_version", side_effect=mock_version):
            mismatches = check_tool_versions.check_versions(pyproject)

        assert mismatches == []

    def test_dict_dependency_format(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry.dependencies]
pyright = {version = "^1.1.408"}
"""
        )

        with patch("check_tool_versions.installed_version", return_value="1.1.410"):
            mismatches = check_tool_versions.check_versions(pyproject)

        assert mismatches == []
