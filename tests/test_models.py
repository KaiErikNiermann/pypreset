"""Tests for configuration models."""

from pypreset.models import (
    CoverageConfig,
    Dependencies,
    DirectoryStructure,
    FileTemplate,
    FormattingConfig,
    FormattingTool,
    Metadata,
    OverrideOptions,
    PresetConfig,
    ProjectConfig,
    TestingConfig,
    TestingFramework,
    TypingLevel,
)


class TestMetadata:
    """Tests for Metadata model."""

    def test_minimal_metadata(self) -> None:
        """Test creating metadata with minimal fields."""
        metadata = Metadata(name="test-project")
        assert metadata.name == "test-project"
        assert metadata.version == "0.1.0"
        assert metadata.python_version == "3.11"

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        metadata = Metadata(
            name="my-project",
            version="1.0.0",
            description="A test project",
            authors=["Test Author <test@example.com>"],
            license="MIT",
            python_version="3.12",
            keywords=["test", "example"],
        )
        assert metadata.name == "my-project"
        assert metadata.version == "1.0.0"
        assert "Test Author" in metadata.authors[0]


class TestTestingConfig:
    """Tests for TestingConfig model."""

    def test_default_testing_config(self) -> None:
        """Test default testing configuration."""
        config = TestingConfig()
        assert config.enabled is True
        assert config.framework == TestingFramework.PYTEST
        assert config.coverage is False

    def test_disabled_testing(self) -> None:
        """Test disabled testing configuration."""
        config = TestingConfig(enabled=False)
        assert config.enabled is False


class TestFormattingConfig:
    """Tests for FormattingConfig model."""

    def test_default_formatting_config(self) -> None:
        """Test default formatting configuration."""
        config = FormattingConfig()
        assert config.enabled is True
        assert config.tool == FormattingTool.RUFF
        assert config.line_length == 100

    def test_black_formatting(self) -> None:
        """Test black formatting configuration."""
        config = FormattingConfig(tool=FormattingTool.BLACK, line_length=88)
        assert config.tool == FormattingTool.BLACK
        assert config.line_length == 88


class TestDirectoryStructure:
    """Tests for DirectoryStructure model."""

    def test_empty_structure(self) -> None:
        """Test empty directory structure."""
        structure = DirectoryStructure()
        assert structure.directories == []
        assert structure.files == []

    def test_with_directories_and_files(self) -> None:
        """Test structure with directories and files."""
        structure = DirectoryStructure(
            directories=["src", "tests", "docs"],
            files=[
                FileTemplate(path="README.md", content="# Test"),
                FileTemplate(path="main.py", template="main.py.j2"),
            ],
        )
        assert len(structure.directories) == 3
        assert len(structure.files) == 2


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_minimal_project_config(self) -> None:
        """Test minimal project configuration."""
        config = ProjectConfig(
            metadata=Metadata(name="test-project"),
        )
        assert config.metadata.name == "test-project"
        assert config.testing.enabled is True
        assert config.formatting.enabled is True
        assert config.typing_level == TypingLevel.STRICT

    def test_full_project_config(self) -> None:
        """Test full project configuration."""
        config = ProjectConfig(
            metadata=Metadata(
                name="full-project",
                version="2.0.0",
                description="A complete project",
            ),
            structure=DirectoryStructure(directories=["data", "models"]),
            dependencies=Dependencies(
                main=["pandas", "numpy"],
                dev=["pytest"],
            ),
            testing=TestingConfig(enabled=True, coverage=True),
            formatting=FormattingConfig(tool=FormattingTool.RUFF),
            typing_level=TypingLevel.STRICT,
        )
        assert config.metadata.name == "full-project"
        assert len(config.dependencies.main) == 2
        assert config.testing.coverage_config.enabled is True


class TestPresetConfig:
    """Tests for PresetConfig model."""

    def test_minimal_preset(self) -> None:
        """Test minimal preset configuration."""
        preset = PresetConfig(name="test-preset")
        assert preset.name == "test-preset"
        assert preset.base is None

    def test_preset_with_base(self) -> None:
        """Test preset with inheritance."""
        preset = PresetConfig(
            name="extended-preset",
            description="An extended preset",
            base="empty-package",
        )
        assert preset.base == "empty-package"


class TestOverrideOptions:
    """Tests for OverrideOptions model."""

    def test_empty_overrides(self) -> None:
        """Test empty override options."""
        overrides = OverrideOptions()
        assert overrides.testing_enabled is None
        assert overrides.extra_packages == []

    def test_full_overrides(self) -> None:
        """Test full override options."""
        overrides = OverrideOptions(
            testing_enabled=False,
            formatting_enabled=True,
            python_version="3.12",
            typing_level=TypingLevel.BASIC,
            extra_packages=["requests", "httpx"],
            extra_dev_packages=["pytest-asyncio"],
        )
        assert overrides.testing_enabled is False
        assert len(overrides.extra_packages) == 2


class TestDockerConfig:
    """Tests for DockerConfig model."""

    def test_default_disabled(self) -> None:
        """Test default docker config is disabled."""
        from pypreset.models import DockerConfig

        config = DockerConfig()
        assert config.enabled is False
        assert config.base_image is None
        assert config.devcontainer is False

    def test_enabled_with_custom_image(self) -> None:
        """Test docker config with custom base image."""
        from pypreset.models import DockerConfig

        config = DockerConfig(enabled=True, base_image="ubuntu:22.04")
        assert config.enabled is True
        assert config.base_image == "ubuntu:22.04"

    def test_docker_on_project_config(self) -> None:
        """Test docker config as part of ProjectConfig."""
        from pypreset.models import DockerConfig

        config = ProjectConfig(
            metadata=Metadata(name="docker-test"),
            docker=DockerConfig(enabled=True),
        )
        assert config.docker.enabled is True
        assert config.docker.base_image is None

    def test_partial_docker_config(self) -> None:
        """Test partial docker config for presets."""
        from pypreset.models import PartialDockerConfig

        partial = PartialDockerConfig()
        assert partial.enabled is None
        assert partial.base_image is None
        assert partial.devcontainer is None

    def test_devcontainer_enabled(self) -> None:
        """Test docker config with devcontainer enabled."""
        from pypreset.models import DockerConfig

        config = DockerConfig(enabled=True, devcontainer=True)
        assert config.devcontainer is True

    def test_container_runtime_default(self) -> None:
        """Test default container runtime is docker."""
        from pypreset.models import ContainerRuntime, DockerConfig

        config = DockerConfig()
        assert config.container_runtime == ContainerRuntime.DOCKER

    def test_container_runtime_podman(self) -> None:
        """Test setting container runtime to podman."""
        from pypreset.models import ContainerRuntime, DockerConfig

        config = DockerConfig(container_runtime=ContainerRuntime.PODMAN)
        assert config.container_runtime == ContainerRuntime.PODMAN


class TestContainerRuntime:
    """Tests for ContainerRuntime enum."""

    def test_values(self) -> None:
        from pypreset.models import ContainerRuntime

        assert ContainerRuntime.DOCKER == "docker"
        assert ContainerRuntime.PODMAN == "podman"


class TestCoverageConfig:
    """Tests for CoverageConfig and coverage bool coercion."""

    def test_default_coverage_config(self) -> None:
        from pypreset.models import CoverageConfig, CoverageTool

        config = CoverageConfig()
        assert config.enabled is False
        assert config.tool == CoverageTool.NONE
        assert config.threshold is None
        assert config.ignore_patterns == []

    def test_coverage_bool_true_coercion(self) -> None:
        """Test that coverage=True is coerced to CoverageConfig."""
        config = TestingConfig(enabled=True, coverage=True)
        assert isinstance(config.coverage, CoverageConfig)
        assert config.coverage.enabled is True
        assert config.coverage.tool.value == "codecov"

    def test_coverage_bool_false_coercion(self) -> None:
        """Test that coverage=False is coerced to CoverageConfig."""
        config = TestingConfig(enabled=True, coverage=False)
        assert isinstance(config.coverage, CoverageConfig)
        assert config.coverage.enabled is False

    def test_coverage_dict_passthrough(self) -> None:
        """Test that coverage dict is parsed as CoverageConfig."""
        from pypreset.models import CoverageConfig

        config = TestingConfig(
            enabled=True,
            coverage={"enabled": True, "tool": "codecov", "threshold": 80},
        )
        assert isinstance(config.coverage, CoverageConfig)
        assert config.coverage.threshold == 80

    def test_coverage_config_property(self) -> None:
        """Test coverage_config property always returns CoverageConfig."""
        config = TestingConfig(enabled=True, coverage=True)
        cc = config.coverage_config
        assert isinstance(cc, CoverageConfig)
        assert cc.enabled is True


class TestDocumentationConfig:
    """Tests for DocumentationConfig model."""

    def test_default(self) -> None:
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = DocumentationConfig()
        assert config.enabled is False
        assert config.tool == DocumentationTool.NONE
        assert config.deploy_gh_pages is False

    def test_mkdocs(self) -> None:
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = DocumentationConfig(
            enabled=True, tool=DocumentationTool.MKDOCS, deploy_gh_pages=True
        )
        assert config.tool == DocumentationTool.MKDOCS
        assert config.deploy_gh_pages is True

    def test_sphinx(self) -> None:
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = DocumentationConfig(enabled=True, tool=DocumentationTool.SPHINX)
        assert config.tool == DocumentationTool.SPHINX

    def test_on_project_config(self) -> None:
        from pypreset.models import DocumentationConfig, DocumentationTool

        config = ProjectConfig(
            metadata=Metadata(name="docs-test"),
            documentation=DocumentationConfig(enabled=True, tool=DocumentationTool.MKDOCS),
        )
        assert config.documentation.enabled is True
        assert config.documentation.tool == DocumentationTool.MKDOCS


class TestToxConfig:
    """Tests for ToxConfig model."""

    def test_default(self) -> None:
        from pypreset.models import ToxConfig

        config = ToxConfig()
        assert config.enabled is False

    def test_enabled(self) -> None:
        from pypreset.models import ToxConfig

        config = ToxConfig(enabled=True)
        assert config.enabled is True

    def test_on_project_config(self) -> None:
        from pypreset.models import ToxConfig

        config = ProjectConfig(
            metadata=Metadata(name="tox-test"),
            tox=ToxConfig(enabled=True),
        )
        assert config.tox.enabled is True


class TestNewOverrideOptions:
    """Tests for new OverrideOptions fields."""

    def test_new_override_defaults(self) -> None:
        overrides = OverrideOptions()
        assert overrides.container_runtime is None
        assert overrides.coverage_enabled is None
        assert overrides.coverage_tool is None
        assert overrides.coverage_threshold is None
        assert overrides.docs_enabled is None
        assert overrides.docs_tool is None
        assert overrides.docs_deploy_gh_pages is None
        assert overrides.tox_enabled is None

    def test_new_overrides_set(self) -> None:
        from pypreset.models import ContainerRuntime, CoverageTool, DocumentationTool

        overrides = OverrideOptions(
            container_runtime=ContainerRuntime.PODMAN,
            coverage_enabled=True,
            coverage_tool=CoverageTool.CODECOV,
            coverage_threshold=80,
            docs_enabled=True,
            docs_tool=DocumentationTool.MKDOCS,
            docs_deploy_gh_pages=True,
            tox_enabled=True,
        )
        assert overrides.container_runtime == ContainerRuntime.PODMAN
        assert overrides.coverage_threshold == 80
        assert overrides.docs_tool == DocumentationTool.MKDOCS
        assert overrides.tox_enabled is True
