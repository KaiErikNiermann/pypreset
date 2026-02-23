"""Template engine for rendering project files."""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pypreset.docker_utils import resolve_docker_base_image as _resolve_base_image
from pypreset.models import ProjectConfig

logger = logging.getLogger(__name__)


def get_templates_dir() -> Path:
    """Get the directory containing built-in templates."""
    return Path(__file__).parent / "templates"


def create_jinja_environment() -> Environment:
    """Create a Jinja2 environment with the templates directory."""
    templates_dir = get_templates_dir()
    return Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def get_template_context(config: ProjectConfig) -> dict[str, Any]:
    """Build the template context from a project configuration."""
    # Convert package name to module name (replace hyphens with underscores)
    package_name = config.metadata.name.replace("-", "_")

    return {
        "project": {
            "name": config.metadata.name,
            "package_name": package_name,
            "version": config.metadata.version,
            "description": config.metadata.description,
            "authors": config.metadata.authors,
            "license": config.metadata.license,
            "readme": config.metadata.readme,
            "python_version": config.metadata.python_version,
            "keywords": config.metadata.keywords,
            "classifiers": config.metadata.classifiers,
        },
        "dependencies": {
            "main": config.dependencies.main,
            "dev": config.dependencies.dev,
            "optional": config.dependencies.optional,
        },
        "testing": {
            "enabled": config.testing.enabled,
            "framework": config.testing.framework.value,
            "coverage": config.testing.coverage_config.enabled,
            "coverage_config": {
                "enabled": config.testing.coverage_config.enabled,
                "tool": config.testing.coverage_config.tool.value,
                "threshold": config.testing.coverage_config.threshold,
                "ignore_patterns": config.testing.coverage_config.ignore_patterns,
            },
        },
        "formatting": {
            "enabled": config.formatting.enabled,
            "tool": config.formatting.tool.value,
            "line_length": config.formatting.line_length,
            "radon": config.formatting.radon,
            "pre_commit": config.formatting.pre_commit,
            "version_bumping": config.formatting.version_bumping,
            "type_checker": config.formatting.type_checker.value,
        },
        "dependabot": {
            "enabled": config.dependabot.enabled,
            "schedule": config.dependabot.schedule,
            "open_pull_requests_limit": config.dependabot.open_pull_requests_limit,
        },
        "docker": {
            "enabled": config.docker.enabled,
            "base_image": _resolve_base_image(
                config.metadata.python_version, config.docker.base_image
            ),
            "devcontainer": config.docker.devcontainer,
            "container_runtime": config.docker.container_runtime.value,
        },
        "documentation": {
            "enabled": config.documentation.enabled,
            "tool": config.documentation.tool.value,
            "deploy_gh_pages": config.documentation.deploy_gh_pages,
        },
        "tox": {
            "enabled": config.tox.enabled,
        },
        "typing_level": config.typing_level.value,
        "layout": config.layout.value,
        "package_manager": config.package_manager.value,
        "entry_points": [{"name": ep.name, "module": ep.module} for ep in config.entry_points],
        "extras": config.extras,
    }


def render_template(env: Environment, template_name: str, context: dict[str, Any]) -> str:
    """Render a template with the given context."""
    template = env.get_template(template_name)
    return template.render(**context)


def render_content(content: str, context: dict[str, Any]) -> str:
    """Render inline content (not from a template file)."""
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.from_string(content)
    return template.render(**context)


def render_path(path_template: str, context: dict[str, Any]) -> str:
    """Render a path template (e.g., 'src/{{ project.package_name }}')."""
    env = Environment()
    template = env.from_string(path_template)
    return template.render(**context)
