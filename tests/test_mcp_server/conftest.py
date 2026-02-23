"""Shared fixtures for MCP server tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from fastmcp import Client

from pypreset.mcp_server import create_server


@pytest_asyncio.fixture
async def mcp_client() -> AsyncGenerator[Client]:
    """Provide a connected in-memory FastMCP client."""
    server = create_server()
    async with Client(server) as client:
        yield client
