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


class TestDockerfileGeneration:
    """Tests for Docker file generation."""

    def test_docker_disabled_no_files(self, temp_output_dir: Path) -> None:
        """Test that no Docker files are created when disabled."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="no-docker"),
            docker=DockerConfig(enabled=False),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert not (project_dir / "Dockerfile").exists()
        assert not (project_dir / ".dockerignore").exists()

    def test_docker_enabled_creates_files(self, temp_output_dir: Path) -> None:
        """Test that Docker files are created when enabled."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="docker-test"),
            docker=DockerConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "Dockerfile").exists()
        assert (project_dir / ".dockerignore").exists()

    def test_docker_poetry_template(self, temp_output_dir: Path) -> None:
        """Test that Poetry Dockerfile uses poetry export."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="poetry-docker"),
            docker=DockerConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "poetry" in content
        assert "poetry export" in content

    def test_docker_uv_template(self, temp_output_dir: Path) -> None:
        """Test that uv Dockerfile uses uv sync."""
        from pypreset.models import CreationPackageManager, DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="uv-docker"),
            package_manager=CreationPackageManager.UV,
            docker=DockerConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "uv sync" in content
        assert "astral-sh" in content

    def test_docker_src_layout(self, temp_output_dir: Path) -> None:
        """Test Dockerfile with src layout."""
        from pypreset.models import DockerConfig, LayoutStyle

        config = ProjectConfig(
            metadata=Metadata(name="src-docker"),
            layout=LayoutStyle.SRC,
            docker=DockerConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "COPY src/" in content

    def test_docker_flat_layout(self, temp_output_dir: Path) -> None:
        """Test Dockerfile with flat layout."""
        from pypreset.models import DockerConfig, LayoutStyle

        config = ProjectConfig(
            metadata=Metadata(name="flat-docker"),
            layout=LayoutStyle.FLAT,
            docker=DockerConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "COPY flat_docker/" in content

    def test_docker_with_entry_points(self, temp_output_dir: Path) -> None:
        """Test Dockerfile with entry points uses ENTRYPOINT."""
        from pypreset.models import DockerConfig, EntryPoint

        config = ProjectConfig(
            metadata=Metadata(name="cli-docker"),
            docker=DockerConfig(enabled=True),
            entry_points=[EntryPoint(name="mycli", module="cli_docker.cli:app")],
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "ENTRYPOINT" in content
        assert "mycli" in content

    def test_docker_custom_base_image(self, temp_output_dir: Path) -> None:
        """Test Dockerfile uses custom base image."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="custom-base"),
            docker=DockerConfig(enabled=True, base_image="ubuntu:22.04"),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / "Dockerfile").read_text()
        assert "ubuntu:22.04" in content


class TestDevcontainerGeneration:
    """Tests for devcontainer generation."""

    def test_devcontainer_disabled_no_files(self, temp_output_dir: Path) -> None:
        """Test that no devcontainer files are created when disabled."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="no-devcontainer"),
            docker=DockerConfig(devcontainer=False),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert not (project_dir / ".devcontainer").exists()

    def test_devcontainer_enabled_creates_files(self, temp_output_dir: Path) -> None:
        """Test that devcontainer.json is created when enabled."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="devcontainer-test"),
            docker=DockerConfig(devcontainer=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        devcontainer_path = project_dir / ".devcontainer" / "devcontainer.json"
        assert devcontainer_path.exists()

        content = devcontainer_path.read_text()
        assert "devcontainer-test" in content
        assert "ms-python.python" in content

    def test_devcontainer_uv_has_features(self, temp_output_dir: Path) -> None:
        """Test that uv devcontainer includes uv feature."""
        from pypreset.models import CreationPackageManager, DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="uv-devcontainer"),
            package_manager=CreationPackageManager.UV,
            docker=DockerConfig(devcontainer=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / ".devcontainer" / "devcontainer.json").read_text()
        assert "uv" in content


class TestPodmanGeneration:
    """Tests for Podman container runtime support."""

    def test_podman_creates_containerfile(self, temp_output_dir: Path) -> None:
        """Test that podman runtime uses Containerfile and .containerignore."""
        from pypreset.models import ContainerRuntime, DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="podman-test"),
            docker=DockerConfig(enabled=True, container_runtime=ContainerRuntime.PODMAN),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "Containerfile").exists()
        assert (project_dir / ".containerignore").exists()
        assert not (project_dir / "Dockerfile").exists()
        assert not (project_dir / ".dockerignore").exists()

    def test_docker_runtime_creates_dockerfile(self, temp_output_dir: Path) -> None:
        """Test that docker runtime uses Dockerfile."""
        from pypreset.models import ContainerRuntime, DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="docker-test-rt"),
            docker=DockerConfig(enabled=True, container_runtime=ContainerRuntime.DOCKER),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "Dockerfile").exists()
        assert not (project_dir / "Containerfile").exists()

    def test_podman_devcontainer_has_userns(self, temp_output_dir: Path) -> None:
        """Test that podman devcontainer has userns=keep-id."""
        from pypreset.models import ContainerRuntime, DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="podman-devc"),
            docker=DockerConfig(
                devcontainer=True,
                container_runtime=ContainerRuntime.PODMAN,
            ),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        content = (project_dir / ".devcontainer" / "devcontainer.json").read_text()
        assert "userns=keep-id" in content


class TestCodecovGeneration:
    """Tests for codecov.yml generation."""

    def test_codecov_generated_when_enabled(self, temp_output_dir: Path) -> None:
        """Test codecov.yml is created when coverage tool is codecov."""
        from pypreset.models import CoverageConfig, CoverageTool

        config = ProjectConfig(
            metadata=Metadata(name="codecov-test"),
            testing=TestingConfig(
                enabled=True,
                coverage=CoverageConfig(enabled=True, tool=CoverageTool.CODECOV, threshold=80),
            ),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        codecov_path = project_dir / "codecov.yml"
        assert codecov_path.exists()
        content = codecov_path.read_text()
        assert "80%" in content

    def test_no_codecov_when_disabled(self, temp_output_dir: Path) -> None:
        """Test no codecov.yml when coverage is disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="no-codecov"),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert not (project_dir / "codecov.yml").exists()


class TestDocumentationGeneration:
    """Tests for documentation scaffolding generation."""

    def test_mkdocs_scaffolding(self, temp_output_dir: Path) -> None:
        """Test MkDocs documentation scaffolding."""
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = ProjectConfig(
            metadata=Metadata(name="mkdocs-test"),
            documentation=DocumentationConfig(enabled=True, tool=DocumentationTool.MKDOCS),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "mkdocs.yml").exists()
        assert (project_dir / "docs" / "index.md").exists()

        content = (project_dir / "mkdocs.yml").read_text()
        assert "mkdocs-test" in content
        assert "material" in content

    def test_sphinx_scaffolding(self, temp_output_dir: Path) -> None:
        """Test Sphinx documentation scaffolding."""
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = ProjectConfig(
            metadata=Metadata(name="sphinx-test"),
            documentation=DocumentationConfig(enabled=True, tool=DocumentationTool.SPHINX),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert (project_dir / "docs" / "conf.py").exists()
        assert (project_dir / "docs" / "index.rst").exists()

        content = (project_dir / "docs" / "conf.py").read_text()
        assert "sphinx-test" in content
        assert "sphinx_rtd_theme" in content

    def test_docs_gh_pages_workflow(self, temp_output_dir: Path) -> None:
        """Test GitHub Pages deploy workflow is generated."""
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = ProjectConfig(
            metadata=Metadata(name="docs-gh"),
            documentation=DocumentationConfig(
                enabled=True, tool=DocumentationTool.MKDOCS, deploy_gh_pages=True
            ),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        workflow_path = project_dir / ".github" / "workflows" / "docs.yaml"
        assert workflow_path.exists()
        content = workflow_path.read_text()
        assert "Deploy Documentation" in content
        assert "mkdocs" in content

    def test_no_docs_when_disabled(self, temp_output_dir: Path) -> None:
        """Test no docs generated when disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="no-docs"),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert not (project_dir / "mkdocs.yml").exists()
        assert not (project_dir / "docs" / "conf.py").exists()


class TestToxGeneration:
    """Tests for tox.ini generation."""

    def test_tox_generated_when_enabled(self, temp_output_dir: Path) -> None:
        """Test tox.ini is created when tox is enabled."""
        from pypreset.models import ToxConfig

        config = ProjectConfig(
            metadata=Metadata(name="tox-test"),
            tox=ToxConfig(enabled=True),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        tox_path = project_dir / "tox.ini"
        assert tox_path.exists()
        content = tox_path.read_text()
        assert "tox-uv" in content
        assert "pytest" in content

    def test_no_tox_when_disabled(self, temp_output_dir: Path) -> None:
        """Test no tox.ini when disabled."""
        config = ProjectConfig(
            metadata=Metadata(name="no-tox"),
        )
        generator = ProjectGenerator(config, temp_output_dir)
        project_dir = generator.generate()

        assert not (project_dir / "tox.ini").exists()
