"""Tests for project validation functionality."""

from pathlib import Path

from pysetup.validator import (
    ProjectValidator,
    ValidationResult,
    validate_project,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_passed_result(self) -> None:
        """Test a passing validation result."""
        result = ValidationResult(True, "Test passed")
        assert result.passed is True
        assert bool(result) is True
        assert "✓" in repr(result)

    def test_failed_result(self) -> None:
        """Test a failing validation result."""
        result = ValidationResult(False, "Test failed", "Some details")
        assert result.passed is False
        assert bool(result) is False
        assert "✗" in repr(result)
        assert result.details == "Some details"


class TestProjectValidator:
    """Tests for ProjectValidator class."""

    def test_validate_nonexistent_project(self, tmp_path: Path) -> None:
        """Test validation of non-existent project."""
        project_dir = tmp_path / "nonexistent"
        validator = ProjectValidator(project_dir)
        results = validator.validate_all()

        assert not validator.is_valid()
        assert any("does not exist" in r.message for r in results)

    def test_validate_empty_directory(self, tmp_path: Path) -> None:
        """Test validation of empty directory."""
        project_dir = tmp_path / "empty"
        project_dir.mkdir()

        validator = ProjectValidator(project_dir)
        validator.validate_all()

        assert not validator.is_valid()

    def test_validate_minimal_project(self, tmp_path: Path) -> None:
        """Test validation of minimal valid project."""
        project_dir = tmp_path / "minimal"
        project_dir.mkdir()

        # Create minimal structure
        (project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "minimal"
version = "0.1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
""")
        (project_dir / "README.md").write_text("# Minimal")
        (project_dir / ".gitignore").write_text("__pycache__/")

        src_dir = project_dir / "src" / "minimal"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text('"""Minimal package."""')

        validator = ProjectValidator(project_dir)
        results = validator.validate_all()

        assert validator.is_valid(), f"Failed: {[r.message for r in results if not r.passed]}"

    def test_validate_missing_pyproject(self, tmp_path: Path) -> None:
        """Test validation fails when pyproject.toml is missing."""
        project_dir = tmp_path / "no_pyproject"
        project_dir.mkdir()
        (project_dir / "README.md").write_text("# Test")

        validator = ProjectValidator(project_dir)
        results = validator.validate_all()

        assert not validator.is_valid()
        assert any("pyproject.toml" in r.message and not r.passed for r in results)

    def test_validate_missing_src(self, tmp_path: Path) -> None:
        """Test validation fails when src directory is missing."""
        project_dir = tmp_path / "no_src"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")

        validator = ProjectValidator(project_dir)
        results = validator.validate_all()

        assert not validator.is_valid()
        assert any("src" in r.message.lower() and not r.passed for r in results)

    def test_validate_invalid_toml(self, tmp_path: Path) -> None:
        """Test validation fails for invalid TOML."""
        project_dir = tmp_path / "invalid_toml"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("this is not valid toml { [ }")

        src_dir = project_dir / "src" / "test"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").touch()

        validator = ProjectValidator(project_dir)
        results = validator.validate_all()

        assert any("invalid" in r.message.lower() for r in results)


class TestValidateProject:
    """Tests for validate_project function."""

    def test_validate_valid_project(self, tmp_path: Path) -> None:
        """Test validating a valid project."""
        project_dir = tmp_path / "valid"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "valid"
version = "0.1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
""")
        (project_dir / "README.md").write_text("# Valid")
        (project_dir / ".gitignore").write_text("")

        src_dir = project_dir / "src" / "valid"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")

        is_valid, results = validate_project(project_dir)

        assert is_valid
        assert all(r.passed for r in results)

    def test_validate_invalid_project(self, tmp_path: Path) -> None:
        """Test validating an invalid project."""
        project_dir = tmp_path / "invalid"
        project_dir.mkdir()
        # Empty directory

        is_valid, results = validate_project(project_dir)

        assert not is_valid
        assert any(not r.passed for r in results)
