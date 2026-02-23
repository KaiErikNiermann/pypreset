"""Tests for MCP server tools."""

import json
from pathlib import Path

import pytest
from fastmcp import Client


@pytest.mark.asyncio
class TestListPresets:
    """Tests for the list_presets tool."""

    async def test_returns_preset_list(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("list_presets", {})
        data = json.loads(result.data)

        assert isinstance(data, list)
        assert len(data) > 0

        names = [p["name"] for p in data]
        assert "empty-package" in names
        assert "cli-tool" in names

    async def test_presets_have_descriptions(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("list_presets", {})
        data = json.loads(result.data)

        for preset in data:
            assert "name" in preset
            assert "description" in preset


@pytest.mark.asyncio
class TestShowPreset:
    """Tests for the show_preset tool."""

    async def test_show_existing_preset(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("show_preset", {"preset_name": "empty-package"})
        data = json.loads(result.data)

        assert data["name"] == "empty-package"
        assert "description" in data

    async def test_show_nonexistent_preset_raises(self, mcp_client: Client) -> None:
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("show_preset", {"preset_name": "does-not-exist"})


@pytest.mark.asyncio
class TestCreateProject:
    """Tests for the create_project tool."""

    async def test_create_basic_project(self, mcp_client: Client, tmp_path: Path) -> None:
        result = await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "test-project",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
                "install_dependencies": False,
            },
        )
        data = json.loads(result.data)

        assert data["project_name"] == "test-project"
        assert data["preset"] == "empty-package"

        project_dir = Path(data["project_dir"])
        assert project_dir.exists()
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "README.md").exists()

    async def test_create_with_overrides(self, mcp_client: Client, tmp_path: Path) -> None:
        result = await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "override-test",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
                "layout": "flat",
                "package_manager": "uv",
            },
        )
        data = json.loads(result.data)

        assert data["layout"] == "flat"
        assert data["package_manager"] == "uv"

        project_dir = Path(data["project_dir"])
        # flat layout — package dir is directly under project, not under src/
        assert (project_dir / "override_test" / "__init__.py").exists()
        assert not (project_dir / "src").exists()


@pytest.mark.asyncio
class TestValidateProject:
    """Tests for the validate_project tool."""

    async def test_validate_valid_project(self, mcp_client: Client, tmp_path: Path) -> None:
        # First create a project
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "valid-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        # Then validate it
        result = await mcp_client.call_tool(
            "validate_project",
            {"project_dir": str(tmp_path / "valid-proj")},
        )
        data = json.loads(result.data)

        assert data["valid"] is True
        assert all(c["passed"] for c in data["checks"])

    async def test_validate_empty_dir(self, mcp_client: Client, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()

        result = await mcp_client.call_tool(
            "validate_project",
            {"project_dir": str(empty)},
        )
        data = json.loads(result.data)

        assert data["valid"] is False


@pytest.mark.asyncio
class TestUserConfig:
    """Tests for user config tools."""

    async def test_get_user_config(self, mcp_client: Client) -> None:
        result = await mcp_client.call_tool("get_user_config", {})
        data = json.loads(result.data)

        assert "config_path" in data
        assert "values" in data
        assert isinstance(data["values"], dict)

    async def test_set_user_config(
        self, mcp_client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Point config path to tmp_path to avoid mutating real config
        config_file = tmp_path / "config.yaml"
        monkeypatch.setattr("pypreset.user_config.CONFIG_FILE", config_file)
        monkeypatch.setattr("pypreset.user_config.CONFIG_DIR", tmp_path)

        result = await mcp_client.call_tool(
            "set_user_config",
            {"values": {"layout": "flat", "python_version": "3.13"}},
        )
        data = json.loads(result.data)

        assert data["values"]["layout"] == "flat"
        assert data["values"]["python_version"] == "3.13"
        assert config_file.exists()


@pytest.mark.asyncio
class TestAugmentProject:
    """Tests for the augment_project tool."""

    async def test_augment_existing_project(self, mcp_client: Client, tmp_path: Path) -> None:
        # Create a minimal project with pyproject.toml
        project_dir = tmp_path / "existing-proj"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "existing-proj"\nversion = "0.1.0"\n'
            "[tool.poetry.dependencies]\n"
            'python = "^3.12"\n'
        )
        (project_dir / "src").mkdir()
        pkg = project_dir / "src" / "existing_proj"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('"""Package."""\n')

        result = await mcp_client.call_tool(
            "augment_project",
            {
                "project_dir": str(project_dir),
                "generate_test_workflow": False,
                "generate_lint_workflow": False,
                "generate_dependabot": False,
                "generate_tests_dir": True,
                "generate_gitignore": True,
            },
        )
        data = json.loads(result.data)

        assert data["success"] is True
        created_paths = [f["path"] for f in data["files_created"]]
        assert any("gitignore" in p for p in created_paths) or any(
            "test" in p for p in created_paths
        )
