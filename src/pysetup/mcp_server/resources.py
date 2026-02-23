"""MCP resource handlers — read-only data exposed to AI assistants."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register all resource handlers on the given MCP server."""

    @mcp.resource(
        "preset://list",
        name="Available Presets",
        description="List of all available project presets with names and descriptions.",
        mime_type="application/json",
    )
    def preset_list() -> str:
        from pysetup.preset_loader import list_available_presets

        presets = list_available_presets()
        return json.dumps([{"name": name, "description": desc} for name, desc in presets])

    @mcp.resource(
        "config://user",
        name="User Configuration",
        description="Current user-level default configuration values.",
        mime_type="application/json",
    )
    def user_config() -> str:
        from pysetup.user_config import get_config_path, load_user_config

        config = load_user_config()
        return json.dumps(
            {
                "config_path": str(get_config_path()),
                "values": config,
            }
        )

    @mcp.resource(
        "template://list",
        name="Available Templates",
        description="List of Jinja2 template files available for project generation.",
        mime_type="application/json",
    )
    def template_list() -> str:
        from pysetup.template_engine import get_templates_dir

        templates_dir = get_templates_dir()
        templates = (
            sorted(p.name for p in templates_dir.glob("*.j2")) if templates_dir.exists() else []
        )
        return json.dumps(templates)
