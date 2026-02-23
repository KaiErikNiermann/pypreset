"""Tests for MCP server resources."""

import json

import pytest
from fastmcp import Client


@pytest.mark.asyncio
class TestPresetListResource:
    """Tests for the preset://list resource."""

    async def test_returns_json_preset_list(self, mcp_client: Client) -> None:
        content = await mcp_client.read_resource("preset://list")
        data = json.loads(content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0
        names = [p["name"] for p in data]
        assert "empty-package" in names

    async def test_preset_entries_have_required_fields(self, mcp_client: Client) -> None:
        content = await mcp_client.read_resource("preset://list")
        data = json.loads(content[0].text)

        for preset in data:
            assert "name" in preset
            assert "description" in preset


@pytest.mark.asyncio
class TestUserConfigResource:
    """Tests for the config://user resource."""

    async def test_returns_config_dict(self, mcp_client: Client) -> None:
        content = await mcp_client.read_resource("config://user")
        data = json.loads(content[0].text)

        assert "config_path" in data
        assert "values" in data
        assert isinstance(data["values"], dict)


@pytest.mark.asyncio
class TestTemplateListResource:
    """Tests for the template://list resource."""

    async def test_returns_template_names(self, mcp_client: Client) -> None:
        content = await mcp_client.read_resource("template://list")
        data = json.loads(content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0
        assert all(t.endswith(".j2") for t in data)

    async def test_contains_core_templates(self, mcp_client: Client) -> None:
        content = await mcp_client.read_resource("template://list")
        data = json.loads(content[0].text)

        assert "pyproject.toml.j2" in data
        assert "README.md.j2" in data
        assert "gitignore.j2" in data
