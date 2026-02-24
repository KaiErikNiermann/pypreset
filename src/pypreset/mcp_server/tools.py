"""MCP tool handlers — actions an AI assistant can invoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

if TYPE_CHECKING:
    from fastmcp import FastMCP

from pypreset.models import (
    ContainerRuntime,  # noqa: F401
    CoverageTool,  # noqa: F401
    CreationPackageManager,
    DocumentationTool,  # noqa: F401
    LayoutStyle,
    OverrideOptions,
    TypeChecker,
    TypingLevel,
)


def register_tools(mcp: FastMCP) -> None:
    """Register all tool handlers on the given MCP server."""

    # ------------------------------------------------------------------
    # create_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="create_project",
        description=(
            "Create a new Python project from a preset. "
            "Returns the path to the generated project directory."
        ),
        tags={"project", "create"},
    )
    def create_project(
        project_name: Annotated[str, Field(description="Name for the new project (e.g. 'my-app')")],
        preset: Annotated[
            str, Field(description="Preset name (e.g. 'empty-package', 'cli-tool', 'data-science')")
        ],
        output_dir: Annotated[str, Field(description="Directory to create the project in")] = ".",
        initialize_git: Annotated[bool, Field(description="Initialize a git repository")] = True,
        install_dependencies: Annotated[
            bool, Field(description="Run package manager install after generation")
        ] = False,
        layout: Annotated[
            str | None, Field(description="Layout style override: 'src' or 'flat'")
        ] = None,
        type_checker: Annotated[
            str | None,
            Field(description="Type checker override: 'mypy', 'pyright', 'ty', or 'none'"),
        ] = None,
        package_manager: Annotated[
            str | None, Field(description="Package manager override: 'poetry' or 'uv'")
        ] = None,
        typing_level: Annotated[
            str | None,
            Field(description="Typing strictness override: 'none', 'basic', or 'strict'"),
        ] = None,
        python_version: Annotated[
            str | None, Field(description="Python version override (e.g. '3.12')")
        ] = None,
        docker: Annotated[bool, Field(description="Generate Dockerfile and .dockerignore")] = False,
        devcontainer: Annotated[
            bool, Field(description="Generate .devcontainer/ configuration")
        ] = False,
        container_runtime: Annotated[
            str | None,
            Field(description="Container runtime: 'docker' or 'podman'"),
        ] = None,
        docs: Annotated[
            str | None,
            Field(description="Documentation tool: 'sphinx', 'mkdocs', or 'none'"),
        ] = None,
        docs_gh_pages: Annotated[
            bool, Field(description="Generate GitHub Pages deploy workflow for docs")
        ] = False,
        tox: Annotated[bool, Field(description="Generate tox.ini with tox-uv")] = False,
        coverage_tool: Annotated[
            str | None,
            Field(description="Coverage service: 'codecov' or 'none'"),
        ] = None,
        coverage_threshold: Annotated[
            int | None,
            Field(description="Minimum coverage percentage"),
        ] = None,
    ) -> str:
        from pypreset.generator import generate_project
        from pypreset.preset_loader import build_project_config

        # Derive docs_enabled from docs param
        docs_enabled = True if docs and docs != "none" else None

        # Derive coverage_enabled from coverage_tool param
        coverage_enabled = True if coverage_tool and coverage_tool != "none" else None

        overrides = OverrideOptions(
            testing_enabled=None,
            formatting_enabled=None,
            radon_enabled=None,
            pre_commit_enabled=None,
            version_bumping_enabled=None,
            layout=LayoutStyle(layout) if layout else None,
            type_checker=TypeChecker(type_checker) if type_checker else None,
            package_manager=CreationPackageManager(package_manager) if package_manager else None,
            typing_level=TypingLevel(typing_level) if typing_level else None,
            python_version=python_version,
            docker_enabled=docker if docker else None,
            devcontainer_enabled=devcontainer if devcontainer else None,
            container_runtime=ContainerRuntime(container_runtime) if container_runtime else None,
            coverage_enabled=coverage_enabled,
            coverage_tool=CoverageTool(coverage_tool) if coverage_tool else None,
            coverage_threshold=coverage_threshold,
            docs_enabled=docs_enabled,
            docs_tool=DocumentationTool(docs) if docs else None,
            docs_deploy_gh_pages=docs_gh_pages if docs_gh_pages else None,
            tox_enabled=tox if tox else None,
        )

        config = build_project_config(
            project_name=project_name,
            preset_name=preset,
            overrides=overrides,
        )

        project_path = generate_project(
            config=config,
            output_dir=Path(output_dir),
            initialize_git=initialize_git,
            install_dependencies=install_dependencies,
        )

        return json.dumps(
            {
                "project_dir": str(project_path),
                "project_name": project_name,
                "preset": preset,
                "layout": config.layout.value,
                "package_manager": config.package_manager.value,
                "docker_enabled": config.docker.enabled,
                "devcontainer_enabled": config.docker.devcontainer,
                "container_runtime": config.docker.container_runtime.value,
                "documentation_enabled": config.documentation.enabled,
                "documentation_tool": config.documentation.tool.value,
                "tox_enabled": config.tox.enabled,
                "coverage_enabled": config.testing.coverage_config.enabled,
                "coverage_tool": config.testing.coverage_config.tool.value,
            }
        )

    # ------------------------------------------------------------------
    # validate_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="validate_project",
        description="Validate the structural correctness of a generated project directory.",
        tags={"project", "validate"},
    )
    def validate_project(
        project_dir: Annotated[str, Field(description="Path to the project directory to validate")],
    ) -> str:
        from pypreset.validator import validate_project as _validate

        is_valid, results = _validate(Path(project_dir))

        return json.dumps(
            {
                "valid": is_valid,
                "checks": [
                    {
                        "passed": r.passed,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in results
                ],
            }
        )

    # ------------------------------------------------------------------
    # list_presets
    # ------------------------------------------------------------------
    @mcp.tool(
        name="list_presets",
        description="List all available project presets with their descriptions.",
        tags={"preset"},
    )
    def list_presets() -> str:
        from pypreset.preset_loader import list_available_presets

        presets = list_available_presets()
        return json.dumps([{"name": name, "description": desc} for name, desc in presets])

    # ------------------------------------------------------------------
    # show_preset
    # ------------------------------------------------------------------
    @mcp.tool(
        name="show_preset",
        description="Show the full configuration of a specific preset.",
        tags={"preset"},
    )
    def show_preset(
        preset_name: Annotated[str, Field(description="Name of the preset to show")],
    ) -> str:
        from pypreset.preset_loader import load_preset

        preset = load_preset(preset_name)
        return json.dumps(preset.model_dump(exclude_none=True), default=str)

    # ------------------------------------------------------------------
    # get_user_config
    # ------------------------------------------------------------------
    @mcp.tool(
        name="get_user_config",
        description="Read the current user-level default configuration.",
        tags={"config"},
    )
    def get_user_config() -> str:
        from pypreset.user_config import get_config_path, load_user_config

        config = load_user_config()
        return json.dumps(
            {
                "config_path": str(get_config_path()),
                "values": config,
            }
        )

    # ------------------------------------------------------------------
    # set_user_config
    # ------------------------------------------------------------------
    @mcp.tool(
        name="set_user_config",
        description=(
            "Update user-level default configuration values. "
            "Merges provided keys into existing config."
        ),
        tags={"config"},
    )
    def set_user_config(
        values: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Key-value pairs to set (e.g. {'layout': 'src', 'python_version': '3.12'})"
                )
            ),
        ],
    ) -> str:
        from pypreset.user_config import load_user_config, save_user_config

        current = load_user_config()
        current.update(values)
        path = save_user_config(current)
        return json.dumps({"config_path": str(path), "values": current})

    # ------------------------------------------------------------------
    # augment_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="augment_project",
        description=(
            "Add CI workflows, tests, gitignore, and/or dependabot to an existing project. "
            "Analyzes the project first, then generates selected components."
        ),
        tags={"project", "augment"},
    )
    def augment_project(
        project_dir: Annotated[str, Field(description="Path to the existing project directory")],
        force: Annotated[bool, Field(description="Overwrite existing files if they exist")] = False,
        generate_test_workflow: Annotated[
            bool, Field(description="Generate test CI workflow")
        ] = True,
        generate_lint_workflow: Annotated[
            bool, Field(description="Generate lint CI workflow")
        ] = True,
        generate_dependabot: Annotated[bool, Field(description="Generate dependabot.yml")] = True,
        generate_tests_dir: Annotated[bool, Field(description="Generate tests directory")] = True,
        generate_gitignore: Annotated[bool, Field(description="Generate .gitignore")] = True,
        generate_dockerfile: Annotated[
            bool, Field(description="Generate Dockerfile and .dockerignore")
        ] = False,
        generate_devcontainer: Annotated[
            bool, Field(description="Generate .devcontainer/ configuration")
        ] = False,
        generate_codecov: Annotated[bool, Field(description="Generate codecov.yml")] = False,
        generate_documentation: Annotated[
            bool, Field(description="Generate documentation scaffolding")
        ] = False,
        documentation_tool: Annotated[
            str, Field(description="Documentation tool: 'sphinx' or 'mkdocs'")
        ] = "sphinx",
        generate_tox: Annotated[bool, Field(description="Generate tox.ini")] = False,
    ) -> str:
        from pypreset.augment_generator import augment_project as _augment
        from pypreset.interactive_prompts import InteractivePrompter
        from pypreset.project_analyzer import analyze_project

        path = Path(project_dir)
        analysis = analyze_project(path)

        # Build config non-interactively
        prompter = InteractivePrompter(analysis)
        config = prompter.build_augment_config(interactive=False)

        # Override component selections
        config.generate_test_workflow = generate_test_workflow
        config.generate_lint_workflow = generate_lint_workflow
        config.generate_dependabot = generate_dependabot
        config.generate_tests_dir = generate_tests_dir
        config.generate_gitignore = generate_gitignore
        config.generate_dockerfile = generate_dockerfile
        config.generate_devcontainer = generate_devcontainer
        config.generate_codecov = generate_codecov
        config.generate_documentation = generate_documentation
        config.documentation_tool = documentation_tool
        config.generate_tox = generate_tox

        result = _augment(project_dir=path, config=config, force=force)

        return json.dumps(
            {
                "success": result.success,
                "files_created": [
                    {"path": str(f.path), "overwritten": f.overwritten}
                    for f in result.files_created
                ],
                "files_skipped": [str(p) for p in result.files_skipped],
                "errors": result.errors,
            }
        )

    # ------------------------------------------------------------------
    # set_project_metadata
    # ------------------------------------------------------------------
    @mcp.tool(
        name="set_project_metadata",
        description=(
            "Set or update PyPI metadata (description, authors, license, URLs, keywords) "
            "in an existing project's pyproject.toml. Only updates fields that are currently "
            "empty unless overwrite=True. Returns publish-readiness warnings for any "
            "fields that are still empty or using placeholder defaults."
        ),
        tags={"project", "metadata"},
    )
    def set_project_metadata(
        project_dir: Annotated[str, Field(description="Path to the project directory")],
        description: Annotated[
            str | None, Field(description="Short package description for PyPI")
        ] = None,
        authors: Annotated[
            list[str] | None,
            Field(description="Authors list, e.g. ['Name <email@example.com>']"),
        ] = None,
        license: Annotated[
            str | None, Field(description="SPDX license identifier (e.g. 'MIT', 'Apache-2.0')")
        ] = None,
        keywords: Annotated[list[str] | None, Field(description="PyPI search keywords")] = None,
        classifiers: Annotated[
            list[str] | None,
            Field(description="PyPI trove classifiers"),
        ] = None,
        repository_url: Annotated[str | None, Field(description="Source repository URL")] = None,
        homepage_url: Annotated[str | None, Field(description="Project homepage URL")] = None,
        documentation_url: Annotated[
            str | None, Field(description="Documentation site URL")
        ] = None,
        bug_tracker_url: Annotated[str | None, Field(description="Issue/bug tracker URL")] = None,
        github_owner: Annotated[
            str | None,
            Field(
                description=(
                    "GitHub owner/org name — auto-generates repository, homepage, "
                    "and bug tracker URLs from this (e.g. 'myuser' or 'myorg')"
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Overwrite existing non-empty values (default: only fill blanks)"),
        ] = False,
    ) -> str:
        from pypreset.metadata_utils import (
            generate_default_urls,
            read_pyproject_metadata,
            set_pyproject_metadata,
        )

        path = Path(project_dir)

        # Read current metadata to get project name for URL generation
        current = read_pyproject_metadata(path)

        # Build updates dict from non-None arguments
        updates: dict[str, Any] = {}
        if description is not None:
            updates["description"] = description
        if authors is not None:
            updates["authors"] = authors
        if license is not None:
            updates["license"] = license
        if keywords is not None:
            updates["keywords"] = keywords
        if classifiers is not None:
            updates["classifiers"] = classifiers
        if repository_url is not None:
            updates["repository_url"] = repository_url
        if homepage_url is not None:
            updates["homepage_url"] = homepage_url
        if documentation_url is not None:
            updates["documentation_url"] = documentation_url
        if bug_tracker_url is not None:
            updates["bug_tracker_url"] = bug_tracker_url

        # Auto-generate URLs from github_owner if provided
        if github_owner:
            auto_urls = generate_default_urls(current["name"], github_owner)
            for key, value in auto_urls.items():
                updates.setdefault(key, value)

        warnings = set_pyproject_metadata(path, updates, overwrite=overwrite)

        return json.dumps(
            {
                "updated_fields": list(updates.keys()),
                "warnings": warnings,
                "metadata": read_pyproject_metadata(path),
            }
        )
