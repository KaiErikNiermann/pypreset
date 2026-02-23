"""Tests for the project analyzer module."""

from pathlib import Path

from pysetup.project_analyzer import (
    DetectedLinter,
    DetectedTestFramework,
    DetectedTypeChecker,
    PackageManager,
    ProjectAnalyzer,
    analyze_project,
)


class TestProjectAnalyzer:
    """Tests for ProjectAnalyzer class."""

    def test_analyze_missing_pyproject(self, tmp_path: Path) -> None:
        """Test analyzing a directory without pyproject.toml."""
        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.project_name is None
        assert len(analysis.missing_fields) > 0
        assert any(f.name == "pyproject.toml" for f in analysis.missing_fields)

    def test_analyze_poetry_project(self, tmp_path: Path) -> None:
        """Test analyzing a Poetry project."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "my-test-project"
version = "1.0.0"
description = "A test project"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
ruff = "^0.5.0"

[tool.ruff]
line-length = 100

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
        )

        # Create src layout
        src_dir = tmp_path / "src" / "my_test_project"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.project_name is not None
        assert analysis.project_name.value == "my-test-project"
        assert analysis.project_name.confidence == "high"

        assert analysis.package_name is not None
        assert analysis.package_name.value == "my_test_project"

        assert analysis.python_version is not None
        assert analysis.python_version.value == "3.11"

        assert analysis.package_manager is not None
        assert analysis.package_manager.value == PackageManager.POETRY

        assert analysis.test_framework is not None
        assert analysis.test_framework.value == DetectedTestFramework.PYTEST

        assert analysis.linter is not None
        assert analysis.linter.value == DetectedLinter.RUFF

        assert analysis.line_length is not None
        assert analysis.line_length.value == 100

        assert analysis.has_src_layout is True

    def test_analyze_pep621_project(self, tmp_path: Path) -> None:
        """Test analyzing a PEP 621 project."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "pep621-project"
version = "2.0.0"
description = "A PEP 621 project"
requires-python = ">=3.10"
dependencies = ["requests"]

[project.optional-dependencies]
dev = ["pytest", "mypy"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
"""
        )

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.project_name is not None
        assert analysis.project_name.value == "pep621-project"

        assert analysis.python_version is not None
        assert analysis.python_version.value == "3.10"

        assert analysis.package_manager is not None
        assert analysis.package_manager.value == PackageManager.SETUPTOOLS

    def test_analyze_with_poetry_lock(self, tmp_path: Path) -> None:
        """Test that poetry.lock increases confidence."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "locked-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
        )
        (tmp_path / "poetry.lock").write_text("# lock file")

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.package_manager is not None
        assert analysis.package_manager.value == PackageManager.POETRY
        assert analysis.package_manager.confidence == "high"

    def test_detect_tests_directory(self, tmp_path: Path) -> None:
        """Test detection of tests directory."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "test-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
"""
        )

        # Create tests directory with test files
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_main.py").write_text("def test_main(): pass")
        (tests_dir / "test_utils.py").write_text("def test_utils(): pass")

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.has_tests_dir is True
        assert len(analysis.existing_tests) == 2

    def test_detect_github_workflows(self, tmp_path: Path) -> None:
        """Test detection of GitHub workflows."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "github-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
"""
        )

        # Create GitHub structure
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yaml").write_text("name: CI")
        (workflows_dir / "release.yml").write_text("name: Release")

        github_dir = tmp_path / ".github"
        (github_dir / "dependabot.yml").write_text("version: 2")

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.has_github_dir is True
        assert len(analysis.existing_workflows) == 2
        assert analysis.has_dependabot is True

    def test_detect_type_checker_mypy(self, tmp_path: Path) -> None:
        """Test detection of mypy type checker."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "typed-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.group.dev.dependencies]
mypy = "^1.10.0"

[tool.mypy]
python_version = "3.11"
strict = true
"""
        )

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.type_checker is not None
        assert analysis.type_checker.value == DetectedTypeChecker.MYPY
        assert analysis.type_checker.confidence == "high"

    def test_detect_type_checker_pyright(self, tmp_path: Path) -> None:
        """Test detection of pyright type checker."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "typed-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.group.dev.dependencies]
pyright = "^1.1.0"
"""
        )

        analyzer = ProjectAnalyzer(tmp_path)
        analysis = analyzer.analyze()

        assert analysis.type_checker is not None
        assert analysis.type_checker.value == DetectedTypeChecker.PYRIGHT


class TestAnalyzeProject:
    """Tests for the analyze_project convenience function."""

    def test_analyze_project_function(self, tmp_path: Path) -> None:
        """Test the convenience function."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "convenience-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
"""
        )

        analysis = analyze_project(tmp_path)

        assert analysis.project_name is not None
        assert analysis.project_name.value == "convenience-project"


class TestDetectedValue:
    """Tests for DetectedValue class."""

    def test_is_reliable_high_confidence(self, tmp_path: Path) -> None:
        """Test that high confidence is reliable."""
        from pysetup.project_analyzer import DetectedValue

        value = DetectedValue("test", "high", "source")
        assert value.is_reliable is True

    def test_is_reliable_medium_confidence(self, tmp_path: Path) -> None:
        """Test that medium confidence is not reliable."""
        from pysetup.project_analyzer import DetectedValue

        value = DetectedValue("test", "medium", "source")
        assert value.is_reliable is False

    def test_is_reliable_low_confidence(self, tmp_path: Path) -> None:
        """Test that low confidence is not reliable."""
        from pysetup.project_analyzer import DetectedValue

        value = DetectedValue("test", "low", "source")
        assert value.is_reliable is False
