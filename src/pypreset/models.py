"""Configuration models for pypreset."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class LayoutStyle(str, Enum):
    """Project directory layout style.

    See https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
    """

    SRC = "src"
    FLAT = "flat"


class TypingLevel(str, Enum):
    """Python typing strictness level."""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


class TestingFramework(str, Enum):
    """Supported testing frameworks."""

    PYTEST = "pytest"
    UNITTEST = "unittest"
    NONE = "none"


class FormattingTool(str, Enum):
    """Supported formatting/linting tools."""

    RUFF = "ruff"
    BLACK = "black"
    NONE = "none"


class TypeChecker(str, Enum):
    """Supported type checking tools."""

    MYPY = "mypy"
    PYRIGHT = "pyright"
    TY = "ty"
    NONE = "none"


class CreationPackageManager(str, Enum):
    """Package manager for project creation."""

    POETRY = "poetry"
    UV = "uv"


class FileTemplate(BaseModel):
    """A file template definition."""

    path: str = Field(..., description="Relative path within the project")
    template: str | None = Field(None, description="Jinja2 template name to use")
    content: str | None = Field(None, description="Inline content (if no template)")
    executable: bool = Field(False, description="Whether the file should be executable")


class DirectoryStructure(BaseModel):
    """Directory structure definition."""

    directories: list[str] = Field(
        default_factory=list, description="List of directories to create"
    )
    files: list[FileTemplate] = Field(default_factory=list, description="List of files to create")  # type: ignore[arg-type]


class DependencyGroup(BaseModel):
    """A group of dependencies."""

    packages: list[str] = Field(default_factory=list, description="List of packages")


class Dependencies(BaseModel):
    """Project dependencies configuration."""

    main: list[str] = Field(default_factory=list, description="Main dependencies")
    dev: list[str] = Field(default_factory=list, description="Development dependencies")
    optional: dict[str, list[str]] = Field(
        default_factory=dict, description="Optional dependency groups"
    )


class TestingConfig(BaseModel):
    """Testing configuration."""

    enabled: bool = Field(True, description="Whether testing is enabled")
    framework: TestingFramework = Field(
        TestingFramework.PYTEST, description="Testing framework to use"
    )
    coverage: bool = Field(False, description="Whether to include coverage tools")


class FormattingConfig(BaseModel):
    """Code formatting configuration."""

    enabled: bool = Field(True, description="Whether formatting is enabled")
    tool: FormattingTool = Field(FormattingTool.RUFF, description="Formatting tool to use")
    line_length: int = Field(100, description="Maximum line length")
    radon: bool = Field(False, description="Enable radon complexity checking")
    pre_commit: bool = Field(False, description="Generate pre-commit hooks config")
    version_bumping: bool = Field(
        False, description="Include bump-my-version for version management"
    )
    type_checker: TypeChecker = Field(TypeChecker.MYPY, description="Type checking tool to use")


class DependabotConfig(BaseModel):
    """Dependabot configuration for automatic dependency updates."""

    enabled: bool = Field(True, description="Whether to generate dependabot.yml")
    schedule: Literal["daily", "weekly", "monthly"] = Field(
        "weekly", description="Update check frequency"
    )
    open_pull_requests_limit: int = Field(
        5, description="Maximum number of open PRs for version updates"
    )


class Metadata(BaseModel):
    """Project metadata (mirrors pyproject.toml)."""

    name: str = Field(..., description="Project name")
    version: str = Field("0.1.0", description="Project version")
    description: str = Field("", description="Project description")
    authors: list[str] = Field(default_factory=list, description="Project authors")
    license: str | None = Field(None, description="Project license")
    readme: str = Field("README.md", description="Readme file")
    python_version: str = Field("3.11", description="Minimum Python version")
    keywords: list[str] = Field(default_factory=list, description="Project keywords")
    classifiers: list[str] = Field(default_factory=list, description="PyPI classifiers")


class EntryPoint(BaseModel):
    """Script entry point configuration."""

    name: str = Field(..., description="Command name")
    module: str = Field(..., description="Module path (e.g., 'mypackage.cli:app')")


# Partial models for presets (all fields optional for merging)
class PartialMetadata(BaseModel):
    """Partial metadata for preset configs (all fields optional)."""

    name: str | None = Field(None, description="Project name")
    version: str | None = Field(None, description="Project version")
    description: str | None = Field(None, description="Project description")
    authors: list[str] | None = Field(None, description="Project authors")
    license: str | None = Field(None, description="Project license")
    readme: str | None = Field(None, description="Readme file")
    python_version: str | None = Field(None, description="Minimum Python version")
    keywords: list[str] | None = Field(None, description="Project keywords")
    classifiers: list[str] | None = Field(None, description="PyPI classifiers")


class PartialDirectoryStructure(BaseModel):
    """Partial directory structure for preset configs."""

    directories: list[str] | None = Field(None, description="List of directories to create")
    files: list[FileTemplate] | None = Field(None, description="List of files to create")


class PartialDependencies(BaseModel):
    """Partial dependencies for preset configs."""

    main: list[str] | None = Field(None, description="Main dependencies")
    dev: list[str] | None = Field(None, description="Development dependencies")
    optional: dict[str, list[str]] | None = Field(None, description="Optional dependency groups")


class PartialTestingConfig(BaseModel):
    """Partial testing config for preset configs."""

    enabled: bool | None = Field(None, description="Whether testing is enabled")
    framework: TestingFramework | None = Field(None, description="Testing framework to use")
    coverage: bool | None = Field(None, description="Whether to include coverage tools")


class PartialFormattingConfig(BaseModel):
    """Partial formatting config for preset configs."""

    enabled: bool | None = Field(None, description="Whether formatting is enabled")
    tool: FormattingTool | None = Field(None, description="Formatting tool to use")
    line_length: int | None = Field(None, description="Maximum line length")
    radon: bool | None = Field(None, description="Enable radon complexity checking")
    pre_commit: bool | None = Field(None, description="Generate pre-commit hooks config")
    version_bumping: bool | None = Field(
        None, description="Include bump-my-version for version management"
    )
    type_checker: TypeChecker | None = Field(None, description="Type checking tool to use")


class PartialDependabotConfig(BaseModel):
    """Partial dependabot config for preset configs."""

    enabled: bool | None = Field(None, description="Whether to generate dependabot.yml")
    schedule: Literal["daily", "weekly", "monthly"] | None = Field(
        None, description="Update check frequency"
    )
    open_pull_requests_limit: int | None = Field(
        None, description="Maximum number of open PRs for version updates"
    )


class ProjectConfig(BaseModel):
    """Complete project configuration."""

    metadata: Metadata
    structure: DirectoryStructure = Field(default_factory=DirectoryStructure)  # type: ignore[arg-type]
    dependencies: Dependencies = Field(default_factory=Dependencies)  # type: ignore[arg-type]
    testing: TestingConfig = Field(default_factory=TestingConfig)  # type: ignore[arg-type]
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)  # type: ignore[arg-type]
    dependabot: DependabotConfig = Field(default_factory=DependabotConfig)  # type: ignore[arg-type]
    typing_level: TypingLevel = Field(TypingLevel.STRICT, description="Typing strictness")
    layout: LayoutStyle = Field(LayoutStyle.SRC, description="Project layout style (src or flat)")
    package_manager: CreationPackageManager = Field(
        CreationPackageManager.POETRY, description="Package manager"
    )
    entry_points: list[EntryPoint] = Field(default_factory=list, description="Script entry points")  # type: ignore[arg-type]
    extras: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class PresetConfig(BaseModel):
    """Preset configuration that can be extended/overridden."""

    name: str = Field(..., description="Preset name")
    description: str = Field("", description="Preset description")
    base: str | None = Field(None, description="Base preset to extend")

    # Typed partial configs for better schema generation
    metadata: PartialMetadata = Field(default_factory=PartialMetadata)  # type: ignore[arg-type]
    structure: PartialDirectoryStructure = Field(default_factory=PartialDirectoryStructure)  # type: ignore[arg-type]
    dependencies: PartialDependencies = Field(default_factory=PartialDependencies)  # type: ignore[arg-type]
    testing: PartialTestingConfig = Field(default_factory=PartialTestingConfig)  # type: ignore[arg-type]
    formatting: PartialFormattingConfig = Field(default_factory=PartialFormattingConfig)  # type: ignore[arg-type]
    dependabot: PartialDependabotConfig = Field(default_factory=PartialDependabotConfig)  # type: ignore[arg-type]
    typing_level: TypingLevel | None = None
    layout: LayoutStyle | None = None
    package_manager: CreationPackageManager | None = None
    entry_points: list[EntryPoint] = Field(default_factory=list, description="Script entry points")  # type: ignore[arg-type]
    extras: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class OverrideOptions(BaseModel):
    """Options that can override preset defaults at runtime."""

    testing_enabled: bool | None = Field(None, description="Override testing enabled")
    formatting_enabled: bool | None = Field(None, description="Override formatting enabled")
    radon_enabled: bool | None = Field(None, description="Override radon complexity checking")
    pre_commit_enabled: bool | None = Field(None, description="Override pre-commit hooks")
    version_bumping_enabled: bool | None = Field(
        None, description="Override bump-my-version inclusion"
    )
    python_version: str | None = Field(None, description="Override Python version")
    layout: LayoutStyle | None = Field(None, description="Override layout style (src or flat)")
    extra_packages: list[str] = Field(default_factory=list, description="Additional packages")
    extra_dev_packages: list[str] = Field(
        default_factory=list, description="Additional dev packages"
    )
    typing_level: TypingLevel | None = Field(None, description="Override typing level")
    type_checker: TypeChecker | None = Field(None, description="Override type checker")
    package_manager: CreationPackageManager | None = Field(
        None, description="Override package manager"
    )
