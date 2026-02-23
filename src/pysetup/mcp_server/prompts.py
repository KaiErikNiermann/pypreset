"""MCP prompt handlers — guided workflows for AI assistants."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

from fastmcp.prompts import Message
from pydantic import Field

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompt handlers on the given MCP server."""

    @mcp.prompt(
        name="create-project",
        description="Guided workflow for creating a new Python project from a preset.",
        tags={"project", "create"},
    )
    def create_project_prompt(
        project_name: Annotated[
            str | None, Field(description="Project name, if already known")
        ] = None,
        preset: Annotated[str | None, Field(description="Preset name, if already chosen")] = None,
    ) -> list[Message]:
        from pysetup.preset_loader import list_available_presets

        presets = list_available_presets()
        preset_info = json.dumps(
            [{"name": name, "description": desc} for name, desc in presets],
            indent=2,
        )

        instructions = [
            "You are helping the user create a new Python project using pysetup.",
            "",
            f"Available presets:\n{preset_info}",
            "",
            "Guide the user through these steps:",
            "1. Choose a project name (valid Python package name with hyphens)",
            "2. Select a preset from the list above",
            "3. Ask about optional overrides:",
            "   - Layout style (src or flat)",
            "   - Package manager (poetry or uv)",
            "   - Type checker (mypy, ty, or none)",
            "   - Typing level (none, basic, or strict)",
            "   - Python version",
            "4. Ask for the output directory",
            "5. Call the create_project tool with the collected parameters",
            "6. Optionally validate the generated project with validate_project",
        ]

        if project_name:
            instructions.append(f"\nThe user has already chosen the name: {project_name}")
        if preset:
            instructions.append(f"The user has already chosen the preset: {preset}")

        return [
            Message(role="user", content="\n".join(instructions)),
            Message(
                role="assistant",
                content=(
                    "I'll help you create a new Python project. Let me guide you through the setup."
                ),
            ),
        ]

    @mcp.prompt(
        name="augment-project",
        description=(
            "Guided workflow for augmenting an existing Python project with CI, tests, etc."
        ),
        tags={"project", "augment"},
    )
    def augment_project_prompt(
        project_dir: Annotated[
            str | None, Field(description="Path to the project directory, if known")
        ] = None,
    ) -> list[Message]:
        instructions = [
            "You are helping the user augment an existing Python project using pysetup.",
            "",
            "Guide the user through these steps:",
            "1. Confirm the project directory path",
            "2. Explain which components can be added:",
            "   - Test CI workflow (GitHub Actions)",
            "   - Lint CI workflow (GitHub Actions)",
            "   - Dependabot configuration",
            "   - Tests directory with template test files",
            "   - .gitignore file",
            "3. Ask which components they want to generate",
            "4. Ask if existing files should be overwritten (force mode)",
            "5. Call the augment_project tool with the selected options",
        ]

        if project_dir:
            instructions.append(f"\nThe user's project is at: {project_dir}")

        return [
            Message(role="user", content="\n".join(instructions)),
            Message(
                role="assistant",
                content=(
                    "I'll help you add CI, tests, and other components to your existing project. "
                    "Let me guide you through the options."
                ),
            ),
        ]
