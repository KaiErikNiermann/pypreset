"""Tests for project generator functionality.

Note: Pyright reports missing arguments for Pydantic model instantiations,
but these are false positives as all fields have defaults defined in the models.
"""

from pathlib import Path

import pytest

from pypreset.generator import ProjectGenerator, generate_project
from pypreset.models import (
    DependabotConfig,
    DirectoryStructure,
    FileTemplate,
    FormattingConfig,
    Metadata,
    ProjectConfig,
    TestingConfig,
)
from pypreset.preset_loader import build_project_config
from pypreset.validator import validate_project


class TestProjectGenerator:
    """Tests for ProjectGenerator class."""

    def test_generator_creates_project_dir(self, temp_output_dir: Path) -> None:
        """Test that generator creates the project directory."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert project_dir.exists()
        assert project_dir.is_dir()
        assert project_dir.name == "test-project"

    def test_generator_creates_src_layout(self, temp_output_dir: Path) -> None:
        """Test that generator creates src layout."""
        config = ProjectConfig(
            metadata=Metadata(name="my-package"),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        src_dir = project_dir / "src"
        package_dir = src_dir / "my_package"
        init_file = package_dir / "__init__.py"

        assert src_dir.exists()
        assert package_dir.exists()
        assert init_file.exists()

    def test_generator_creates_pyproject_toml(self, temp_output_dir: Path) -> None:
        """Test that generator creates pyproject.toml."""
        config = ProjectConfig(
            metadata=Metadata(
                name="test-project",
                version="1.0.0",
                description="A test project",
            ),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        pyproject = project_dir / "pyproject.toml"
        assert pyproject.exists()

        content = pyproject.read_text()
        assert 'name = "test-project"' in content
        assert 'version = "1.0.0"' in content

    def test_generator_creates_tests_dir(self, temp_output_dir: Path) -> None:
        """Test that generator creates tests directory when testing is enabled."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            testing=TestingConfig(enabled=True),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        tests_dir = project_dir / "tests"
        assert tests_dir.exists()
        assert (tests_dir / "__init__.py").exists()
        assert (tests_dir / "test_basic.py").exists()

    def test_generator_skips_tests_when_disabled(self, temp_output_dir: Path) -> None:
        """Test that generator skips tests when testing is disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            testing=TestingConfig(enabled=False),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        tests_dir = project_dir / "tests"
        assert not tests_dir.exists()

    def test_generator_creates_github_workflows(self, temp_output_dir: Path) -> None:
        """Test that generator creates GitHub workflow files."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            testing=TestingConfig(enabled=True),
            formatting=FormattingConfig(enabled=True),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        workflows_dir = project_dir / ".github" / "workflows"
        assert workflows_dir.exists()
        assert (workflows_dir / "ci.yaml").exists()

        ci_content = (workflows_dir / "ci.yaml").read_text()
        assert "test:" in ci_content
        assert "lint:" in ci_content
        assert "pytest" in ci_content
        assert "ruff" in ci_content

    def test_generator_skips_workflows_when_disabled(self, temp_output_dir: Path) -> None:
        """Test that generator skips workflows when testing and formatting are disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            testing=TestingConfig(enabled=False),
            formatting=FormattingConfig(enabled=False),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        workflows_dir = project_dir / ".github" / "workflows"
        assert not workflows_dir.exists()

    def test_generator_creates_dependabot(self, temp_output_dir: Path) -> None:
        """Test that generator creates dependabot.yml when enabled."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            dependabot=DependabotConfig(enabled=True, schedule="weekly"),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        dependabot_path = project_dir / ".github" / "dependabot.yml"
        assert dependabot_path.exists()

        content = dependabot_path.read_text()
        assert "pip" in content
        assert "github-actions" in content
        assert "weekly" in content

    def test_generator_skips_dependabot_when_disabled(self, temp_output_dir: Path) -> None:
        """Test that generator skips dependabot.yml when disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
            testing=TestingConfig(enabled=False),
            formatting=FormattingConfig(enabled=False),
            dependabot=DependabotConfig(enabled=False),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        dependabot_path = project_dir / ".github" / "dependabot.yml"
        assert not dependabot_path.exists()

    def test_generator_creates_custom_directories(self, temp_output_dir: Path) -> None:
        """Test that generator creates custom directories."""
        config = ProjectConfig(
            metadata=Metadata(name="data-project"),
            structure=DirectoryStructure(
                directories=["data/raw", "data/processed", "notebooks"],
            ),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "data" / "raw").exists()
        assert (project_dir / "data" / "processed").exists()
        assert (project_dir / "notebooks").exists()

    def test_generator_creates_custom_files(self, temp_output_dir: Path) -> None:
        """Test that generator creates custom files."""
        config = ProjectConfig(
            metadata=Metadata(name="custom-project"),
            structure=DirectoryStructure(
                files=[
                    FileTemplate(
                        path="config.txt",
                        content="key=value\n",
                    ),
                ],
            ),
        )

        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        config_file = project_dir / "config.txt"
        assert config_file.exists()
        assert config_file.read_text() == "key=value\n"


class TestGenerateProject:
    """Tests for generate_project function."""

    def test_generate_empty_package(self, temp_output_dir: Path) -> None:
        """Test generating an empty package project."""
        config = build_project_config(
            project_name="empty-test",
            preset_name="empty-package",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        # Validate the generated project
        is_valid, results = validate_project(project_dir)
        assert is_valid, f"Validation failed: {[r.message for r in results if not r.passed]}"

    def test_generate_cli_tool(self, temp_output_dir: Path) -> None:
        """Test generating a CLI tool project."""
        config = build_project_config(
            project_name="my-cli",
            preset_name="cli-tool",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        # Check CLI-specific files
        cli_file = project_dir / "src" / "my_cli" / "cli.py"
        assert cli_file.exists()

        content = cli_file.read_text()
        assert "typer" in content

        # Validate the generated project
        is_valid, _ = validate_project(project_dir)
        assert is_valid

    def test_generate_data_science(self, temp_output_dir: Path) -> None:
        """Test generating a data science project."""
        config = build_project_config(
            project_name="my-analysis",
            preset_name="data-science",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        # Check data science-specific structure
        assert (project_dir / "data" / "raw").exists()
        assert (project_dir / "data" / "processed").exists()
        assert (project_dir / "notebooks").exists()
        assert (project_dir / "notebooks" / "01_exploration.ipynb").exists()

        # Check data loader
        data_loader = project_dir / "src" / "my_analysis" / "data_loader.py"
        assert data_loader.exists()

        # Validate the generated project
        is_valid, _ = validate_project(project_dir)
        assert is_valid

    def test_generate_discord_bot(self, temp_output_dir: Path) -> None:
        """Test generating a Discord bot project."""
        config = build_project_config(
            project_name="my-bot",
            preset_name="discord-bot",
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        # Check Discord bot-specific files
        bot_file = project_dir / "src" / "my_bot" / "bot.py"
        assert bot_file.exists()

        content = bot_file.read_text()
        assert "discord" in content
        assert "commands" in content

        # Check cogs directory
        cogs_dir = project_dir / "src" / "my_bot" / "cogs"
        assert cogs_dir.exists()

        # Validate the generated project
        is_valid, _ = validate_project(project_dir)
        assert is_valid


class TestGeneratedProjectValidity:
    """Tests that verify generated projects are structurally valid."""

    @pytest.mark.parametrize(
        "preset_name",
        [
            "empty-package",
            "cli-tool",
            "data-science",
            "discord-bot",
        ],
    )
    def test_all_presets_generate_valid_projects(
        self,
        preset_name: str,
        temp_output_dir: Path,
    ) -> None:
        """Test that all presets generate valid projects."""
        config = build_project_config(
            project_name=f"test-{preset_name}",
            preset_name=preset_name,
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        is_valid, results = validate_project(project_dir)

        if not is_valid:
            failed = [r for r in results if not r.passed]
            pytest.fail(f"Preset '{preset_name}' failed validation: {[r.message for r in failed]}")

    @pytest.mark.parametrize(
        "preset_name",
        [
            "empty-package",
            "cli-tool",
            "data-science",
            "discord-bot",
        ],
    )
    def test_all_presets_have_valid_toml(
        self,
        preset_name: str,
        temp_output_dir: Path,
    ) -> None:
        """Test that all presets generate valid TOML files."""
        import tomllib

        config = build_project_config(
            project_name=f"test-{preset_name}",
            preset_name=preset_name,
        )

        project_dir = generate_project(
            config=config,
            output_dir=temp_output_dir,
            initialize_git=False,
            install_dependencies=False,
        )

        pyproject_path = project_dir / "pyproject.toml"

        # Should not raise
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Basic structure checks
        assert "tool" in data
        assert "poetry" in data["tool"]
        assert "build-system" in data
