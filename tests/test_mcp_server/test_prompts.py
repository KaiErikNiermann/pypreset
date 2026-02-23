"""Tests for MCP server prompts."""

import pytest
from fastmcp import Client


def _text_of(msg: object) -> str:
    """Extract text content from a prompt message."""
    content = msg.content  # type: ignore[union-attr]
    if isinstance(content, str):
        return content
    # TextContent object from MCP
    return content.text  # type: ignore[union-attr]


@pytest.mark.asyncio
class TestCreateProjectPrompt:
    """Tests for the create-project prompt."""

    async def test_returns_messages(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("create-project", {})
        assert len(result.messages) == 2

    async def test_includes_preset_info(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("create-project", {})
        text = _text_of(result.messages[0])
        assert "empty-package" in text
        assert "preset" in text.lower()

    async def test_includes_project_name_when_provided(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("create-project", {"project_name": "my-cool-app"})
        text = _text_of(result.messages[0])
        assert "my-cool-app" in text

    async def test_includes_preset_when_provided(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("create-project", {"preset": "cli-tool"})
        text = _text_of(result.messages[0])
        assert "cli-tool" in text


@pytest.mark.asyncio
class TestAugmentProjectPrompt:
    """Tests for the augment-project prompt."""

    async def test_returns_messages(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("augment-project", {})
        assert len(result.messages) == 2

    async def test_lists_components(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt("augment-project", {})
        text = _text_of(result.messages[0])
        assert "workflow" in text.lower()
        assert "dependabot" in text.lower()
        assert "gitignore" in text.lower()

    async def test_includes_project_dir_when_provided(self, mcp_client: Client) -> None:
        result = await mcp_client.get_prompt(
            "augment-project", {"project_dir": "/home/user/my-project"}
        )
        text = _text_of(result.messages[0])
        assert "/home/user/my-project" in text
