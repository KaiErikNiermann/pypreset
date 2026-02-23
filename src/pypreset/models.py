"""Configuration models for pypreset."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class LayoutStyle(StrEnum):
    """Project directory layout style.

    See https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
    """

    SRC = "src"
    FLAT = "flat"


class TypingLevel(StrEnum):
    """Python typing strictness level."""

    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


class TestingFramework(StrEnum):
    """Supported testing frameworks."""

    PYTEST = "pytest"
    UNITTEST = "unittest"
    NONE = "none"


class FormattingTool(StrEnum):
    """Supported formatting/linting tools."""

    RUFF = "ruff"
    BLACK = "black"
    NONE = "none"


class TypeChecker(StrEnum):
    """Supported type checking tools."""

    MYPY = "mypy"
    PYRIGHT = "pyright"
    TY = "ty"
    NONE = "none"


class CreationPackageManager(StrEnum):
    """Package manager for project creation."""

    POETRY = "poetry"
    UV = "uv"


class ContainerRuntime(StrEnum):
    """Container runtime for Dockerfile/Containerfile generation."""

    DOCKER = "docker"
    PODMAN = "podman"


class CoverageTool(StrEnum):
    """Coverage service integration."""

    CODECOV = "codecov"
    NONE = "none"


class DocumentationTool(StrEnum):
    """Documentation generator."""

    SPHINX = "sphinx"
    MKDOCS = "mkdocs"
    NONE = "none"


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


class CoverageConfig(BaseModel):
    """Coverage service configuration."""

    enabled: bool = Field(default=False, description="Whether coverage is enabled")
    tool: CoverageTool = Field(
        default=CoverageTool.NONE, description="Coverage service integration"
    )
    threshold: int | None = Field(default=None, description="Minimum coverage % (e.g. 80)")
    ignore_patterns: list[str] = Field(default_factory=list, description="Paths to exclude")


class TestingConfig(BaseModel):
    """Testing configuration."""

    enabled: bool = Field(True, description="Whether testing is enabled")
    framework: TestingFramework = Field(
        TestingFramework.PYTEST, description="Testing framework to use"
    )
    coverage: bool | CoverageConfig = Field(False, description="Coverage configuration")

    @model_validator(mode="before")
    @classmethod
    def _coerce_coverage(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        cov = data.get("coverage")
        if cov is True:
            data["coverage"] = CoverageConfig(enabled=True, tool=CoverageTool.CODECOV)
        elif cov is False:
            data["coverage"] = CoverageConfig(enabled=False)
        return data

    @property
    def coverage_config(self) -> CoverageConfig:
        """Always return a CoverageConfig, coercing bool if needed."""
        if isinstance(self.coverage, CoverageConfig):
            return self.coverage
        return CoverageConfig(
            enabled=self.coverage, tool=CoverageTool.CODECOV if self.coverage else CoverageTool.NONE
        )


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


class DockerConfig(BaseModel):
    """Docker/Podman configuration for generating Dockerfile/Containerfile."""

    enabled: bool = Field(False, description="Whether to generate Dockerfile and .dockerignore")
    base_image: str | None = Field(
        None, description="Base image override (auto-resolved from python_version if None)"
    )
    devcontainer: bool = Field(False, description="Whether to generate .devcontainer/ config")
    container_runtime: ContainerRuntime = Field(
        ContainerRuntime.DOCKER, description="Container runtime (docker or podman)"
    )


class DocumentationConfig(BaseModel):
    """Documentation generator configuration."""

    enabled: bool = Field(False, description="Whether to generate documentation scaffolding")
    tool: DocumentationTool = Field(DocumentationTool.NONE, description="Documentation tool")
    deploy_gh_pages: bool = Field(False, description="Generate GitHub Pages deploy workflow")


class ToxConfig(BaseModel):
    """tox configuration for multi-environment testing."""

    enabled: bool = Field(False, description="Whether to generate tox.ini")


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


class PartialCoverageConfig(BaseModel):
    """Partial coverage config for preset configs."""

    enabled: bool | None = Field(None, description="Whether coverage is enabled")
    tool: CoverageTool | None = Field(None, description="Coverage service integration")
    threshold: int | None = Field(None, description="Minimum coverage %")
    ignore_patterns: list[str] | None = Field(None, description="Paths to exclude")


class PartialTestingConfig(BaseModel):
    """Partial testing config for preset configs."""

    enabled: bool | None = Field(None, description="Whether testing is enabled")
    framework: TestingFramework | None = Field(None, description="Testing framework to use")
    coverage: bool | PartialCoverageConfig | None = Field(
        None, description="Coverage configuration"
    )


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


class PartialDockerConfig(BaseModel):
    """Partial docker config for preset configs."""

    enabled: bool | None = Field(
        None, description="Whether to generate Dockerfile and .dockerignore"
    )
    base_image: str | None = Field(None, description="Base image override")
    devcontainer: bool | None = Field(None, description="Whether to generate .devcontainer/ config")
    container_runtime: ContainerRuntime | None = Field(
        None, description="Container runtime (docker or podman)"
    )


class PartialDocumentationConfig(BaseModel):
    """Partial documentation config for preset configs."""

    enabled: bool | None = Field(None, description="Whether to generate documentation")
    tool: DocumentationTool | None = Field(None, description="Documentation tool")
    deploy_gh_pages: bool | None = Field(None, description="Deploy to GitHub Pages")


class PartialToxConfig(BaseModel):
    """Partial tox config for preset configs."""

    enabled: bool | None = Field(None, description="Whether to generate tox.ini")


class ProjectConfig(BaseModel):
    """Complete project configuration."""

    metadata: Metadata
    structure: DirectoryStructure = Field(default_factory=DirectoryStructure)  # type: ignore[arg-type]
    dependencies: Dependencies = Field(default_factory=Dependencies)  # type: ignore[arg-type]
    testing: TestingConfig = Field(default_factory=TestingConfig)  # type: ignore[arg-type]
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)  # type: ignore[arg-type]
    dependabot: DependabotConfig = Field(default_factory=DependabotConfig)  # type: ignore[arg-type]
    docker: DockerConfig = Field(default_factory=DockerConfig)  # type: ignore[arg-type]
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)  # type: ignore[arg-type]
    tox: ToxConfig = Field(default_factory=ToxConfig)  # type: ignore[arg-type]
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
    docker: PartialDockerConfig = Field(default_factory=PartialDockerConfig)  # type: ignore[arg-type]
    documentation: PartialDocumentationConfig = Field(default_factory=PartialDocumentationConfig)  # type: ignore[arg-type]
    tox: PartialToxConfig = Field(default_factory=PartialToxConfig)  # type: ignore[arg-type]
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
    docker_enabled: bool | None = Field(None, description="Override Docker generation")
    devcontainer_enabled: bool | None = Field(None, description="Override devcontainer generation")
    container_runtime: ContainerRuntime | None = Field(
        None, description="Override container runtime"
    )
    coverage_enabled: bool | None = Field(None, description="Override coverage enabled")
    coverage_tool: CoverageTool | None = Field(None, description="Override coverage tool")
    coverage_threshold: int | None = Field(None, description="Override coverage threshold")
    docs_enabled: bool | None = Field(None, description="Override documentation generation")
    docs_tool: DocumentationTool | None = Field(None, description="Override documentation tool")
    docs_deploy_gh_pages: bool | None = Field(None, description="Override GH Pages deploy")
    tox_enabled: bool | None = Field(None, description="Override tox generation")
