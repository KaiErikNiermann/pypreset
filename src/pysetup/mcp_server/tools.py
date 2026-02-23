"""MCP tool handlers — actions an AI assistant can invoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

if TYPE_CHECKING:
    from fastmcp import FastMCP

from pysetup.models import (
    CreationPackageManager,
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
            str | None, Field(description="Type checker override: 'mypy', 'ty', or 'none'")
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
    ) -> str:
        from pysetup.generator import generate_project
        from pysetup.preset_loader import build_project_config

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
        from pysetup.validator import validate_project as _validate

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
        from pysetup.preset_loader import list_available_presets

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
        from pysetup.preset_loader import load_preset

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
        from pysetup.user_config import get_config_path, load_user_config

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
        from pysetup.user_config import load_user_config, save_user_config

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
    ) -> str:
        from pysetup.augment_generator import augment_project as _augment
        from pysetup.interactive_prompts import InteractivePrompter
        from pysetup.project_analyzer import analyze_project

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
