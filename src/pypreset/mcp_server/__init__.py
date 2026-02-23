"""MCP server for pypreset — exposes project scaffolding via Model Context Protocol."""

from fastmcp import FastMCP


def create_server() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    mcp = FastMCP(
        name="pypreset",
        instructions=(
            "MCP server for pypreset, a meta-tool that scaffolds Poetry-based Python projects "
            "from YAML presets. Use tools to create/augment projects, list presets, validate "
            "project structure, and manage user configuration."
        ),
    )

    # Import and register tools, resources, prompts
    from pypreset.mcp_server.prompts import register_prompts
    from pypreset.mcp_server.resources import register_resources
    from pypreset.mcp_server.tools import register_tools

    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


def main() -> None:
    """Entry point for the pypreset-mcp CLI command."""
    server = create_server()
    server.run()
