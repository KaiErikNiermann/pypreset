"""Tests for the augment generator module."""

from pathlib import Path

from pypreset.augment_generator import (
    AugmentComponent,
    AugmentOrchestrator,
    DependabotGenerator,
    GitignoreGenerator,
    LintWorkflowGenerator,
    ReadmeGenerator,
    TestsDirectoryGenerator,
    TestWorkflowGenerator,
    augment_project,
)
from pypreset.interactive_prompts import AugmentConfig
from pypreset.project_analyzer import (
    DetectedLinter,
    DetectedTestFramework,
    DetectedTypeChecker,
    PackageManager,
)


def create_test_config(
    project_name: str = "test-project",
    package_name: str = "test_project",
    python_version: str = "3.11",
    package_manager: PackageManager = PackageManager.POETRY,
    test_framework: DetectedTestFramework = DetectedTestFramework.PYTEST,
    linter: DetectedLinter = DetectedLinter.RUFF,
    type_checker: DetectedTypeChecker = DetectedTypeChecker.MYPY,
    generate_test_workflow: bool = True,
    generate_lint_workflow: bool = True,
    generate_dependabot: bool = True,
    generate_tests_dir: bool = True,
    generate_gitignore: bool = True,
    generate_dockerfile: bool = False,
    generate_devcontainer: bool = False,
) -> AugmentConfig:
    """Create an AugmentConfig for testing."""
    return AugmentConfig(
        project_name=project_name,
        package_name=package_name,
        python_version=python_version,
        description="Test project",
        package_manager=package_manager,
        test_framework=test_framework,
        has_coverage=False,
        linter=linter,
        type_checker=type_checker,
        line_length=100,
        source_dirs=["src"],
        has_src_layout=True,
        generate_test_workflow=generate_test_workflow,
        generate_lint_workflow=generate_lint_workflow,
        generate_dependabot=generate_dependabot,
        generate_tests_dir=generate_tests_dir,
        generate_gitignore=generate_gitignore,
        generate_dockerfile=generate_dockerfile,
        generate_devcontainer=generate_devcontainer,
    )


class TestTestWorkflowGenerator:
    """Tests for TestWorkflowGenerator."""

    def test_generates_test_workflow(self, tmp_path: Path) -> None:
        """Test that test workflow is generated."""
        config = create_test_config()
        generator = TestWorkflowGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path(".github/workflows/test.yaml")
        assert (tmp_path / ".github/workflows/test.yaml").exists()

        content = (tmp_path / ".github/workflows/test.yaml").read_text()
        assert "name: Tests" in content
        assert "poetry run pytest" in content

    def test_skips_when_no_test_framework(self, tmp_path: Path) -> None:
        """Test that workflow is skipped when no test framework."""
        config = create_test_config(test_framework=DetectedTestFramework.NONE)
        generator = TestWorkflowGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 0

    def test_should_generate_false_when_disabled(self, tmp_path: Path) -> None:
        """Test that should_generate returns False when disabled."""
        config = create_test_config(generate_test_workflow=False)
        generator = TestWorkflowGenerator(tmp_path, config)

        assert generator.should_generate() is False


class TestLintWorkflowGenerator:
    """Tests for LintWorkflowGenerator."""

    def test_generates_lint_workflow(self, tmp_path: Path) -> None:
        """Test that lint workflow is generated."""
        config = create_test_config()
        generator = LintWorkflowGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path(".github/workflows/lint.yaml")
        assert (tmp_path / ".github/workflows/lint.yaml").exists()

        content = (tmp_path / ".github/workflows/lint.yaml").read_text()
        assert "name: Lint" in content
        assert "ruff check" in content
        assert "mypy" in content

    def test_skips_when_no_linter_or_type_checker(self, tmp_path: Path) -> None:
        """Test that workflow is skipped when no linter or type checker."""
        config = create_test_config(
            linter=DetectedLinter.NONE, type_checker=DetectedTypeChecker.NONE
        )
        generator = LintWorkflowGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 0


class TestDependabotGenerator:
    """Tests for DependabotGenerator."""

    def test_generates_dependabot(self, tmp_path: Path) -> None:
        """Test that dependabot.yml is generated."""
        config = create_test_config()
        generator = DependabotGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path(".github/dependabot.yml")
        assert (tmp_path / ".github/dependabot.yml").exists()

        content = (tmp_path / ".github/dependabot.yml").read_text()
        assert "version: 2" in content
        assert "pip" in content
        assert "github-actions" in content


class TestGitignoreGenerator:
    """Tests for GitignoreGenerator."""

    def test_generates_gitignore(self, tmp_path: Path) -> None:
        """Test that .gitignore file is generated."""
        config = create_test_config()
        generator = GitignoreGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path(".gitignore")
        assert (tmp_path / ".gitignore").exists()

        content = (tmp_path / ".gitignore").read_text()
        assert "__pycache__" in content
        assert ".venv" in content

    def test_skips_when_disabled(self, tmp_path: Path) -> None:
        """Test that gitignore is skipped when disabled."""
        config = create_test_config(generate_gitignore=False)
        generator = GitignoreGenerator(tmp_path, config)

        assert generator.should_generate() is False
        files = generator.generate()
        assert len(files) == 0


class TestTestsDirectoryGenerator:
    """Tests for TestsDirectoryGenerator."""

    def test_generates_tests_directory(self, tmp_path: Path) -> None:
        """Test that tests directory and files are generated."""
        config = create_test_config()
        generator = TestsDirectoryGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 3
        paths = [f.path for f in files]
        assert Path("tests/__init__.py") in paths
        assert Path("tests/conftest.py") in paths
        assert Path("tests/test_basic.py") in paths

        assert (tmp_path / "tests/__init__.py").exists()
        assert (tmp_path / "tests/conftest.py").exists()
        assert (tmp_path / "tests/test_basic.py").exists()

    def test_does_not_overwrite_init(self, tmp_path: Path) -> None:
        """Test that __init__.py is not overwritten."""
        # Create existing tests/__init__.py
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        init_file = tests_dir / "__init__.py"
        init_file.write_text("# Existing content")

        config = create_test_config()
        generator = TestsDirectoryGenerator(tmp_path, config)

        files = generator.generate()

        # __init__.py should be skipped
        paths = [f.path for f in files]
        assert Path("tests/__init__.py") not in paths

        # Original content preserved
        assert init_file.read_text() == "# Existing content"


class TestAugmentOrchestrator:
    """Tests for AugmentOrchestrator."""

    def test_runs_all_generators(self, tmp_path: Path) -> None:
        """Test that orchestrator runs all enabled generators."""
        config = create_test_config()
        orchestrator = AugmentOrchestrator(tmp_path, config)

        result = orchestrator.run()

        assert result.success is True
        # test.yaml, lint.yaml, dependabot, 3 test files, .gitignore
        assert len(result.files_created) == 7
        assert len(result.errors) == 0

    def test_respects_disabled_components(self, tmp_path: Path) -> None:
        """Test that disabled components are skipped."""
        config = create_test_config(
            generate_test_workflow=False,
            generate_lint_workflow=False,
            generate_dependabot=False,
            generate_tests_dir=False,
            generate_gitignore=False,
        )
        orchestrator = AugmentOrchestrator(tmp_path, config)

        result = orchestrator.run()

        assert result.success is True
        assert len(result.files_created) == 0

    def test_runs_specific_components(self, tmp_path: Path) -> None:
        """Test running only specific components."""
        config = create_test_config()
        orchestrator = AugmentOrchestrator(tmp_path, config)

        result = orchestrator.run(components=[AugmentComponent.DEPENDABOT])

        assert result.success is True
        # Only dependabot should be created
        assert len(result.files_created) == 1
        assert result.files_created[0].path == Path(".github/dependabot.yml")


class TestAugmentProject:
    """Tests for the augment_project convenience function."""

    def test_augments_project(self, tmp_path: Path) -> None:
        """Test the convenience function."""
        # Create minimal project structure
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "augment-test"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
"""
        )

        config = create_test_config(project_name="augment-test", package_name="augment_test")
        result = augment_project(tmp_path, config)

        assert result.success is True
        assert len(result.files_created) > 0
        assert (tmp_path / ".github/workflows/test.yaml").exists()
        assert (tmp_path / ".github/workflows/lint.yaml").exists()
        assert (tmp_path / ".github/dependabot.yml").exists()
        assert (tmp_path / "tests/test_basic.py").exists()

    def test_force_overwrites_files(self, tmp_path: Path) -> None:
        """Test that force=True overwrites existing files."""
        # Create existing workflow
        workflows_dir = tmp_path / ".github/workflows"
        workflows_dir.mkdir(parents=True)
        existing = workflows_dir / "test.yaml"
        existing.write_text("# Old content")

        config = create_test_config()
        result = augment_project(tmp_path, config, force=True)

        assert result.success is True
        # File should be overwritten
        new_content = existing.read_text()
        assert "# Old content" not in new_content
        assert "name: Tests" in new_content

        # Check overwritten flag
        overwritten_files = [f for f in result.files_created if f.overwritten]
        assert len(overwritten_files) >= 1


class TestDockerfileGenerator:
    """Tests for DockerfileGenerator."""

    def test_generates_dockerfile_poetry(self, tmp_path: Path) -> None:
        """Test that Dockerfile is generated for Poetry project."""
        from pypreset.augment_generator import DockerfileGenerator

        config = create_test_config(generate_dockerfile=True)
        generator = DockerfileGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 2
        paths = [f.path for f in files]
        assert Path("Dockerfile") in paths
        assert Path(".dockerignore") in paths

        content = (tmp_path / "Dockerfile").read_text()
        assert "poetry" in content

    def test_generates_dockerfile_uv(self, tmp_path: Path) -> None:
        """Test that uv Dockerfile is generated."""
        from pypreset.augment_generator import DockerfileGenerator

        config = create_test_config(generate_dockerfile=True, package_manager=PackageManager.POETRY)
        # PackageManager.POETRY -> Dockerfile.j2 (not uv)
        generator = DockerfileGenerator(tmp_path, config)
        generator.generate()
        content = (tmp_path / "Dockerfile").read_text()
        assert "poetry" in content

    def test_skips_when_disabled(self, tmp_path: Path) -> None:
        """Test that Dockerfile is skipped when disabled."""
        from pypreset.augment_generator import DockerfileGenerator

        config = create_test_config(generate_dockerfile=False)
        generator = DockerfileGenerator(tmp_path, config)

        assert generator.should_generate() is False

    def test_no_overwrite_without_force(self, tmp_path: Path) -> None:
        """Test that existing Dockerfile is not overwritten without force."""
        from pypreset.augment_generator import DockerfileGenerator

        (tmp_path / "Dockerfile").write_text("# Existing Dockerfile")
        config = create_test_config(generate_dockerfile=True)
        generator = DockerfileGenerator(tmp_path, config)

        files = generator.generate(force=False)

        # Dockerfile should be skipped, .dockerignore created
        paths = [f.path for f in files]
        assert Path("Dockerfile") not in paths
        assert (tmp_path / "Dockerfile").read_text() == "# Existing Dockerfile"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        """Test that force=True overwrites existing Dockerfile."""
        from pypreset.augment_generator import DockerfileGenerator

        (tmp_path / "Dockerfile").write_text("# Existing Dockerfile")
        config = create_test_config(generate_dockerfile=True)
        generator = DockerfileGenerator(tmp_path, config)

        files = generator.generate(force=True)

        paths = [f.path for f in files]
        assert Path("Dockerfile") in paths
        assert (tmp_path / "Dockerfile").read_text() != "# Existing Dockerfile"

    def test_dockerignore_content(self, tmp_path: Path) -> None:
        """Test .dockerignore has expected content."""
        from pypreset.augment_generator import DockerfileGenerator

        config = create_test_config(generate_dockerfile=True)
        generator = DockerfileGenerator(tmp_path, config)
        generator.generate()

        content = (tmp_path / ".dockerignore").read_text()
        assert "__pycache__" in content
        assert ".venv" in content
        assert ".git" in content


class TestDevcontainerGenerator:
    """Tests for DevcontainerGenerator."""

    def test_generates_devcontainer(self, tmp_path: Path) -> None:
        """Test that devcontainer.json is generated."""
        from pypreset.augment_generator import DevcontainerGenerator

        config = create_test_config(generate_devcontainer=True)
        generator = DevcontainerGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path(".devcontainer/devcontainer.json")
        assert (tmp_path / ".devcontainer/devcontainer.json").exists()

        content = (tmp_path / ".devcontainer/devcontainer.json").read_text()
        assert "test-project" in content
        assert "ms-python.python" in content

    def test_skips_when_disabled(self, tmp_path: Path) -> None:
        """Test that devcontainer is skipped when disabled."""
        from pypreset.augment_generator import DevcontainerGenerator

        config = create_test_config(generate_devcontainer=False)
        generator = DevcontainerGenerator(tmp_path, config)

        assert generator.should_generate() is False

    def test_no_overwrite_without_force(self, tmp_path: Path) -> None:
        """Test that existing devcontainer.json is not overwritten without force."""
        from pypreset.augment_generator import DevcontainerGenerator

        dc_dir = tmp_path / ".devcontainer"
        dc_dir.mkdir()
        (dc_dir / "devcontainer.json").write_text('{"name": "existing"}')

        config = create_test_config(generate_devcontainer=True)
        generator = DevcontainerGenerator(tmp_path, config)

        files = generator.generate(force=False)

        assert len(files) == 0
        assert (dc_dir / "devcontainer.json").read_text() == '{"name": "existing"}'


class TestReadmeGenerator:
    """Tests for ReadmeGenerator."""

    def _config_with_readme(self, **kwargs: object) -> AugmentConfig:
        """Create an AugmentConfig with generate_readme=True and optional overrides."""
        base = create_test_config()
        base.generate_readme = True
        base.repository_url = "https://github.com/owner/test-project"
        base.license_id = "MIT"
        for k, v in kwargs.items():
            setattr(base, k, v)
        return base

    def test_generates_readme(self, tmp_path: Path) -> None:
        """Test that README.md is generated."""
        config = self._config_with_readme()
        generator = ReadmeGenerator(tmp_path, config)

        files = generator.generate()

        assert len(files) == 1
        assert files[0].path == Path("README.md")
        assert (tmp_path / "README.md").exists()

        content = (tmp_path / "README.md").read_text()
        assert "test-project" in content

    def test_readme_contains_badges(self, tmp_path: Path) -> None:
        """Test that README includes badges from repository URL."""
        config = self._config_with_readme()
        generator = ReadmeGenerator(tmp_path, config)
        generator.generate()

        content = (tmp_path / "README.md").read_text()
        assert "CI" in content
        assert "owner/test-project" in content

    def test_readme_skipped_when_disabled(self, tmp_path: Path) -> None:
        """Test that README is skipped when generate_readme is False."""
        config = create_test_config()
        config.generate_readme = False
        generator = ReadmeGenerator(tmp_path, config)

        assert generator.should_generate() is False

    def test_readme_no_overwrite_without_force(self, tmp_path: Path) -> None:
        """Test that existing README.md is not overwritten without force."""
        (tmp_path / "README.md").write_text("# Existing README")
        config = self._config_with_readme()
        generator = ReadmeGenerator(tmp_path, config)

        files = generator.generate(force=False)

        assert len(files) == 0
        assert (tmp_path / "README.md").read_text() == "# Existing README"

    def test_readme_force_overwrites(self, tmp_path: Path) -> None:
        """Test that force=True overwrites existing README.md."""
        (tmp_path / "README.md").write_text("# Existing README")
        config = self._config_with_readme()
        generator = ReadmeGenerator(tmp_path, config)

        files = generator.generate(force=True)

        assert len(files) == 1
        assert (tmp_path / "README.md").read_text() != "# Existing README"
