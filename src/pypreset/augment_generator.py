"""Augment generator - adds components to existing projects."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from pypreset.docker_utils import resolve_docker_base_image as _resolve_base_image
from pypreset.interactive_prompts import AugmentConfig
from pypreset.project_analyzer import (
    DetectedLinter,
    DetectedTestFramework,
    DetectedTypeChecker,
)

logger = logging.getLogger(__name__)


class AugmentComponent(StrEnum):
    """Available augment components."""

    TEST_WORKFLOW = "test_workflow"
    LINT_WORKFLOW = "lint_workflow"
    DEPENDABOT = "dependabot"
    TESTS_DIR = "tests_dir"
    GITIGNORE = "gitignore"
    CONFTEST = "conftest"
    PRE_COMMIT = "pre_commit"
    PYPI_PUBLISH = "pypi_publish"
    DOCKERFILE = "dockerfile"
    DEVCONTAINER = "devcontainer"


@dataclass
class GeneratedFile:
    """Represents a generated file."""

    path: Path
    content: str
    overwritten: bool = False


@dataclass
class AugmentResult:
    """Result of an augment operation."""

    success: bool
    files_created: list[GeneratedFile]
    files_skipped: list[Path]
    errors: list[str]


def get_augment_templates_dir() -> Path:
    """Get the directory containing augment templates."""
    return Path(__file__).parent / "templates" / "augment"


def create_augment_jinja_env() -> Environment:
    """Create Jinja2 environment for augment templates."""
    # Try augment-specific templates first, fall back to main templates
    augment_dir = get_augment_templates_dir()
    templates_dir = Path(__file__).parent / "templates"

    # Create the augment directory if it doesn't exist
    augment_dir.mkdir(parents=True, exist_ok=True)

    return Environment(
        loader=FileSystemLoader([str(augment_dir), str(templates_dir)]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def get_augment_context(config: AugmentConfig) -> dict[str, Any]:
    """Build template context from augment config."""
    return {
        "project": {
            "name": config.project_name,
            "package_name": config.package_name,
            "python_version": config.python_version,
            "description": config.description,
        },
        "testing": {
            "enabled": config.test_framework != DetectedTestFramework.NONE,
            "framework": config.test_framework.value,
            "coverage": config.has_coverage,
        },
        "formatting": {
            "enabled": config.linter != DetectedLinter.NONE,
            "tool": config.linter.value,
            "line_length": config.line_length,
        },
        "typing": {
            "enabled": config.type_checker != DetectedTypeChecker.NONE,
            "checker": config.type_checker.value,
        },
        "dependabot": {
            "enabled": config.generate_dependabot,
            "schedule": config.dependabot_schedule,
            "open_pull_requests_limit": config.dependabot_pr_limit,
        },
        "source_dirs": config.source_dirs,
        "has_src_layout": config.has_src_layout,
        "layout": "src" if config.has_src_layout else "flat",
        "package_manager": config.package_manager.value,
        "docker": {
            "base_image": _resolve_base_image(config.python_version),
        },
    }


class ComponentGenerator(ABC):
    """Base class for component generators."""

    def __init__(self, project_dir: Path, config: AugmentConfig) -> None:
        self.project_dir = project_dir
        self.config = config
        self.env = create_augment_jinja_env()
        self.context = get_augment_context(config)

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Return the component name for logging."""
        ...

    @abstractmethod
    def should_generate(self) -> bool:
        """Check if this component should be generated."""
        ...

    @abstractmethod
    def generate(self, force: bool = False) -> list[GeneratedFile]:
        """Generate the component files."""
        ...

    def _render_template(self, template_name: str) -> str:
        """Render a template with the current context."""
        template = self.env.get_template(template_name)
        return template.render(**self.context)

    def _write_file(self, path: Path, content: str, force: bool = False) -> GeneratedFile | None:
        """Write content to a file, optionally overwriting."""
        full_path = self.project_dir / path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        overwritten = full_path.exists()
        if overwritten and not force:
            logger.info(f"Skipping {path} (already exists)")
            return None

        full_path.write_text(content)
        logger.info(f"{'Overwrote' if overwritten else 'Created'} {path}")

        return GeneratedFile(path=path, content=content, overwritten=overwritten)


class TestWorkflowGenerator(ComponentGenerator):
    """Generates test workflow for GitHub Actions."""

    @property
    def component_name(self) -> str:
        return "test_workflow"

    def should_generate(self) -> bool:
        return self.config.generate_test_workflow

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        if self.config.test_framework == DetectedTestFramework.NONE:
            logger.warning("Skipping test workflow - no test framework configured")
            return files

        content = self._render_template("test_workflow.yaml.j2")
        path = Path(".github/workflows/test.yaml")

        result = self._write_file(path, content, force)
        if result:
            files.append(result)

        return files


class LintWorkflowGenerator(ComponentGenerator):
    """Generates lint workflow for GitHub Actions."""

    @property
    def component_name(self) -> str:
        return "lint_workflow"

    def should_generate(self) -> bool:
        return self.config.generate_lint_workflow

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        if (
            self.config.linter == DetectedLinter.NONE
            and self.config.type_checker == DetectedTypeChecker.NONE
        ):
            logger.warning("Skipping lint workflow - no linter or type checker configured")
            return files

        content = self._render_template("lint_workflow.yaml.j2")
        path = Path(".github/workflows/lint.yaml")

        result = self._write_file(path, content, force)
        if result:
            files.append(result)

        return files


class DependabotGenerator(ComponentGenerator):
    """Generates dependabot.yml configuration."""

    @property
    def component_name(self) -> str:
        return "dependabot"

    def should_generate(self) -> bool:
        return self.config.generate_dependabot

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        content = self._render_template("dependabot_augment.yml.j2")
        path = Path(".github/dependabot.yml")

        result = self._write_file(path, content, force)
        if result:
            files.append(result)

        return files


class TestsDirectoryGenerator(ComponentGenerator):
    """Generates tests directory and template test file."""

    @property
    def component_name(self) -> str:
        return "tests_dir"

    def should_generate(self) -> bool:
        return self.config.generate_tests_dir

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        # Create tests/__init__.py
        init_path = Path("tests/__init__.py")
        init_content = '"""Tests package."""\n'
        result = self._write_file(
            init_path, init_content, force=False
        )  # Never overwrite __init__.py
        if result:
            files.append(result)

        # Create tests/conftest.py
        conftest_content = self._render_template("conftest.py.j2")
        conftest_path = Path("tests/conftest.py")
        result = self._write_file(conftest_path, conftest_content, force=False)
        if result:
            files.append(result)

        # Create tests/test_basic.py
        test_content = self._render_template("test_template.py.j2")
        test_path = Path("tests/test_basic.py")
        result = self._write_file(test_path, test_content, force=False)
        if result:
            files.append(result)

        return files


class GitignoreGenerator(ComponentGenerator):
    """Generates .gitignore file."""

    @property
    def component_name(self) -> str:
        return "gitignore"

    def should_generate(self) -> bool:
        return self.config.generate_gitignore

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        if not self.should_generate():
            return []

        files: list[GeneratedFile] = []

        content = self._render_template("gitignore.j2")
        path = Path(".gitignore")

        result = self._write_file(path, content, force)
        if result:
            files.append(result)

        return files


class PypiPublishWorkflowGenerator(ComponentGenerator):
    """Generates PyPI publish workflow for GitHub Actions."""

    @property
    def component_name(self) -> str:
        return "pypi_publish"

    def should_generate(self) -> bool:
        return self.config.generate_pypi_publish

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        content = self._render_template("pypi_publish_workflow.yaml.j2")
        path = Path(".github/workflows/publish.yaml")

        result = self._write_file(path, content, force)
        if result:
            files.append(result)

        return files


class DockerfileGenerator(ComponentGenerator):
    """Generates Dockerfile and .dockerignore."""

    @property
    def component_name(self) -> str:
        return "dockerfile"

    def should_generate(self) -> bool:
        return self.config.generate_dockerfile

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        # Select template based on package manager
        if self.config.package_manager.value == "uv":
            template_name = "Dockerfile_uv.j2"
        else:
            template_name = "Dockerfile.j2"

        content = self._render_template(template_name)
        result = self._write_file(Path("Dockerfile"), content, force)
        if result:
            files.append(result)

        ignore_content = self._render_template("dockerignore.j2")
        result = self._write_file(Path(".dockerignore"), ignore_content, force)
        if result:
            files.append(result)

        return files


class DevcontainerGenerator(ComponentGenerator):
    """Generates .devcontainer/devcontainer.json."""

    @property
    def component_name(self) -> str:
        return "devcontainer"

    def should_generate(self) -> bool:
        return self.config.generate_devcontainer

    def generate(self, force: bool = False) -> list[GeneratedFile]:
        files: list[GeneratedFile] = []

        content = self._render_template("devcontainer.json.j2")
        result = self._write_file(Path(".devcontainer/devcontainer.json"), content, force)
        if result:
            files.append(result)

        return files


class AugmentOrchestrator:
    """Orchestrates the augment operation across components."""

    def __init__(self, project_dir: Path, config: AugmentConfig) -> None:
        self.project_dir = project_dir.absolute()
        self.config = config

        # Register all component generators
        self.generators: list[ComponentGenerator] = [
            TestWorkflowGenerator(self.project_dir, config),
            LintWorkflowGenerator(self.project_dir, config),
            DependabotGenerator(self.project_dir, config),
            TestsDirectoryGenerator(self.project_dir, config),
            GitignoreGenerator(self.project_dir, config),
            PypiPublishWorkflowGenerator(self.project_dir, config),
            DockerfileGenerator(self.project_dir, config),
            DevcontainerGenerator(self.project_dir, config),
        ]

    def run(
        self, force: bool = False, components: list[AugmentComponent] | None = None
    ) -> AugmentResult:
        """Run the augment operation."""
        files_created: list[GeneratedFile] = []
        files_skipped: list[Path] = []
        errors: list[str] = []

        for generator in self.generators:
            # Skip if specific components requested and this isn't one of them
            if components is not None:
                component_enum = AugmentComponent(generator.component_name)
                if component_enum not in components:
                    continue

            if not generator.should_generate():
                logger.debug(f"Skipping {generator.component_name} - not enabled")
                continue

            try:
                generated = generator.generate(force=force)
                files_created.extend(generated)
            except Exception as e:
                logger.error(f"Error generating {generator.component_name}: {e}")
                errors.append(f"{generator.component_name}: {str(e)}")

        return AugmentResult(
            success=len(errors) == 0,
            files_created=files_created,
            files_skipped=files_skipped,
            errors=errors,
        )


def augment_project(
    project_dir: Path,
    config: AugmentConfig,
    force: bool = False,
    components: list[AugmentComponent] | None = None,
) -> AugmentResult:
    """Augment an existing project with workflows and tests.

    Args:
        project_dir: Path to the project directory
        config: Augment configuration
        force: Whether to overwrite existing files
        components: Specific components to generate (None = all enabled)

    Returns:
        AugmentResult with details of generated files
    """
    orchestrator = AugmentOrchestrator(project_dir, config)
    return orchestrator.run(force=force, components=components)
