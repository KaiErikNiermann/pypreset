"""MCP server for pysetup — exposes project scaffolding via Model Context Protocol."""

from fastmcp import FastMCP


def create_server() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    mcp = FastMCP(
        name="pysetup",
        instructions=(
            "MCP server for pysetup, a meta-tool that scaffolds Poetry-based Python projects "
            "from YAML presets. Use tools to create/augment projects, list presets, validate "
            "project structure, and manage user configuration."
        ),
    )

    # Import and register tools, resources, prompts
    from pysetup.mcp_server.prompts import register_prompts
    from pysetup.mcp_server.resources import register_resources
    from pysetup.mcp_server.tools import register_tools

    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


def main() -> None:
    """Entry point for the pysetup-mcp CLI command."""
    server = create_server()
    server.run()
