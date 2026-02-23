"""Tests for configuration models."""

from pysetup.models import (
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
        assert config.testing.coverage is True


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
