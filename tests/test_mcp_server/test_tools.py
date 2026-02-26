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

    async def test_create_project_with_docker(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test creating a project with Docker enabled."""
        result = await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "docker-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
                "docker": True,
            },
        )
        data = json.loads(result.data)

        assert data["docker_enabled"] is True
        project_dir = Path(data["project_dir"])
        assert (project_dir / "Dockerfile").exists()
        assert (project_dir / ".dockerignore").exists()

    async def test_create_project_with_devcontainer(
        self, mcp_client: Client, tmp_path: Path
    ) -> None:
        """Test creating a project with devcontainer enabled."""
        result = await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "devcontainer-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
                "devcontainer": True,
            },
        )
        data = json.loads(result.data)

        assert data["devcontainer_enabled"] is True
        project_dir = Path(data["project_dir"])
        assert (project_dir / ".devcontainer" / "devcontainer.json").exists()

    async def test_create_project_default_no_docker(
        self, mcp_client: Client, tmp_path: Path
    ) -> None:
        """Test that default project has no Docker files."""
        result = await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "no-docker",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )
        data = json.loads(result.data)

        assert data["docker_enabled"] is False
        project_dir = Path(data["project_dir"])
        assert not (project_dir / "Dockerfile").exists()

    async def test_augment_with_dockerfile(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test augmenting a project with Dockerfile generation."""
        project_dir = tmp_path / "aug-docker"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "aug-docker"\nversion = "0.1.0"\n'
            "[tool.poetry.dependencies]\n"
            'python = "^3.12"\n'
        )
        (project_dir / "src").mkdir()
        pkg = project_dir / "src" / "aug_docker"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('"""Package."""\n')

        result = await mcp_client.call_tool(
            "augment_project",
            {
                "project_dir": str(project_dir),
                "generate_test_workflow": False,
                "generate_lint_workflow": False,
                "generate_dependabot": False,
                "generate_tests_dir": False,
                "generate_gitignore": False,
                "generate_dockerfile": True,
            },
        )
        data = json.loads(result.data)

        assert data["success"] is True
        created_paths = [f["path"] for f in data["files_created"]]
        assert "Dockerfile" in created_paths
        assert ".dockerignore" in created_paths

    async def test_augment_with_devcontainer(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test augmenting a project with devcontainer generation."""
        project_dir = tmp_path / "aug-devcontainer"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "aug-devcontainer"\nversion = "0.1.0"\n'
            "[tool.poetry.dependencies]\n"
            'python = "^3.12"\n'
        )
        (project_dir / "src").mkdir()
        pkg = project_dir / "src" / "aug_devcontainer"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('"""Package."""\n')

        result = await mcp_client.call_tool(
            "augment_project",
            {
                "project_dir": str(project_dir),
                "generate_test_workflow": False,
                "generate_lint_workflow": False,
                "generate_dependabot": False,
                "generate_tests_dir": False,
                "generate_gitignore": False,
                "generate_devcontainer": True,
            },
        )
        data = json.loads(result.data)

        assert data["success"] is True
        created_paths = [f["path"] for f in data["files_created"]]
        assert ".devcontainer/devcontainer.json" in created_paths


@pytest.mark.asyncio
class TestSetProjectMetadata:
    """Tests for the set_project_metadata tool."""

    async def test_set_metadata_on_poetry_project(self, mcp_client: Client, tmp_path: Path) -> None:
        # Create a project first
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "meta-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        result = await mcp_client.call_tool(
            "set_project_metadata",
            {
                "project_dir": str(tmp_path / "meta-proj"),
                "description": "A really cool package",
                "license": "MIT",
                "keywords": ["python", "cool"],
                "repository_url": "https://github.com/user/meta-proj",
            },
        )
        data = json.loads(result.data)

        assert "description" in data["updated_fields"]
        assert "license" in data["updated_fields"]
        assert data["metadata"]["description"] == "A really cool package"
        assert data["metadata"]["license"] == "MIT"
        assert data["metadata"]["keywords"] == ["python", "cool"]
        assert data["metadata"]["repository_url"] == "https://github.com/user/meta-proj"

    async def test_set_metadata_with_github_owner(self, mcp_client: Client, tmp_path: Path) -> None:
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "gh-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        result = await mcp_client.call_tool(
            "set_project_metadata",
            {
                "project_dir": str(tmp_path / "gh-proj"),
                "github_owner": "myuser",
            },
        )
        data = json.loads(result.data)

        assert data["metadata"]["repository_url"] == "https://github.com/myuser/gh-proj"
        assert data["metadata"]["homepage_url"] == "https://github.com/myuser/gh-proj"
        assert data["metadata"]["bug_tracker_url"] == "https://github.com/myuser/gh-proj/issues"

    async def test_returns_publish_warnings(self, mcp_client: Client, tmp_path: Path) -> None:
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "warn-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        # Set minimal metadata — should still have warnings
        result = await mcp_client.call_tool(
            "set_project_metadata",
            {
                "project_dir": str(tmp_path / "warn-proj"),
                "license": "MIT",
            },
        )
        data = json.loads(result.data)

        assert isinstance(data["warnings"], list)
        assert len(data["warnings"]) > 0


@pytest.mark.asyncio
class TestVerifyWorkflow:
    """Tests for the verify_workflow tool."""

    async def test_act_not_installed(self, mcp_client: Client, tmp_path: Path) -> None:
        """When act is not installed, the tool returns errors and warnings."""
        # Create a project with workflows
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "wf-proj",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        # Mock act as not installed to get predictable results
        from unittest.mock import patch

        from pypreset.act_runner import ActCheckResult

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=False, error="not on PATH"),
            ),
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install from website", None),
            ),
        ):
            result = await mcp_client.call_tool(
                "verify_workflow",
                {
                    "project_dir": str(tmp_path / "wf-proj"),
                },
            )

        data = json.loads(result.data)
        assert data["act_available"] is False
        assert len(data["errors"]) > 0
        assert len(data["warnings"]) > 0

    async def test_successful_dry_run(self, mcp_client: Client, tmp_path: Path) -> None:
        """When act is installed and workflow is valid, returns success."""
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "wf-ok",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        from unittest.mock import patch

        from pypreset.act_runner import ActCheckResult, ActRunResult

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="lint\ntest", return_code=0
        )
        verify_mock = ActRunResult(
            success=True,
            command=["act", "--dryrun", "push"],
            stdout="ok",
            return_code=0,
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = await mcp_client.call_tool(
                "verify_workflow",
                {
                    "project_dir": str(tmp_path / "wf-ok"),
                },
            )

        data = json.loads(result.data)
        assert data["act_available"] is True
        assert data["act_version"] == "act 0.2.60"
        assert len(data["errors"]) == 0
        assert len(data["runs"]) == 2

    async def test_with_specific_workflow(self, mcp_client: Client, tmp_path: Path) -> None:
        """Can target a specific workflow file."""
        await mcp_client.call_tool(
            "create_project",
            {
                "project_name": "wf-specific",
                "preset": "empty-package",
                "output_dir": str(tmp_path),
                "initialize_git": False,
            },
        )

        from unittest.mock import patch

        from pypreset.act_runner import ActCheckResult, ActRunResult

        list_mock = ActRunResult(
            success=True, command=["act", "--list"], stdout="lint", return_code=0
        )
        verify_mock = ActRunResult(
            success=True, command=["act", "--dryrun"], stdout="ok", return_code=0
        )

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=True, version="act 0.2.60"),
            ),
            patch(
                "pypreset.act_runner.run_act",
                side_effect=[list_mock, verify_mock],
            ),
        ):
            result = await mcp_client.call_tool(
                "verify_workflow",
                {
                    "project_dir": str(tmp_path / "wf-specific"),
                    "workflow_file": ".github/workflows/ci.yaml",
                    "job": "lint",
                },
            )

        data = json.loads(result.data)
        assert data["act_available"] is True
        assert data["workflow_path"] == ".github/workflows/ci.yaml"

    async def test_returns_all_fields(self, mcp_client: Client, tmp_path: Path) -> None:
        """Verify the response shape has all expected fields."""
        from unittest.mock import patch

        from pypreset.act_runner import ActCheckResult

        with (
            patch(
                "pypreset.act_runner.check_act",
                return_value=ActCheckResult(installed=False, error="not found"),
            ),
            patch(
                "pypreset.act_runner.get_install_suggestion",
                return_value=("Install act", None),
            ),
        ):
            result = await mcp_client.call_tool(
                "verify_workflow",
                {"project_dir": str(tmp_path)},
            )

        data = json.loads(result.data)
        assert "act_available" in data
        assert "act_version" in data
        assert "workflow_path" in data
        assert "errors" in data
        assert "warnings" in data
        assert "runs" in data


@pytest.mark.asyncio
class TestMigrateToUv:
    """Tests for the migrate_to_uv tool."""

    async def test_not_installed_returns_error(self, mcp_client: Client) -> None:
        from unittest.mock import patch

        with patch("pypreset.migration.shutil.which", return_value=None):
            result = await mcp_client.call_tool(
                "migrate_to_uv",
                {"project_dir": "/tmp/fake-project"},
            )

        data = json.loads(result.data)
        assert data["success"] is False
        assert "not installed" in data["error"]

    async def test_successful_dry_run(self, mcp_client: Client, tmp_path: Path) -> None:
        from unittest.mock import patch

        from pypreset.migration import MigrationResult

        mock_migration_result = MigrationResult(
            success=True,
            command=["migrate-to-uv", "--dry-run", str(tmp_path)],
            stdout="[project]\nname = 'test'",
            stderr="",
            return_code=0,
            dry_run=True,
        )

        with (
            patch("pypreset.migration.check_migrate_to_uv", return_value=(True, "0.11.0")),
            patch("pypreset.migration.migrate_to_uv", return_value=mock_migration_result),
        ):
            result = await mcp_client.call_tool(
                "migrate_to_uv",
                {"project_dir": str(tmp_path), "dry_run": True},
            )

        data = json.loads(result.data)
        assert data["success"] is True
        assert data["dry_run"] is True
        assert data["migrate_to_uv_version"] == "0.11.0"

    async def test_command_failure_returns_error(self, mcp_client: Client, tmp_path: Path) -> None:
        from unittest.mock import patch

        from pypreset.migration import MigrationCommandFailure

        with (
            patch("pypreset.migration.check_migrate_to_uv", return_value=(True, "0.11.0")),
            patch(
                "pypreset.migration.migrate_to_uv",
                side_effect=MigrationCommandFailure(
                    command=["migrate-to-uv", str(tmp_path)],
                    returncode=1,
                    stdout="",
                    stderr="Project is already using uv",
                ),
            ),
        ):
            result = await mcp_client.call_tool(
                "migrate_to_uv",
                {"project_dir": str(tmp_path)},
            )

        data = json.loads(result.data)
        assert data["success"] is False
        assert "already using uv" in data["stderr"]


@pytest.mark.asyncio
class TestGenerateBadges:
    """Tests for the generate_badges tool."""

    async def test_badges_from_poetry_project(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test badge generation from a Poetry project with URLs and license."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "badge-project"
version = "1.0.0"
license = "MIT"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.urls]
Repository = "https://github.com/owner/badge-project"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
        )

        result = await mcp_client.call_tool(
            "generate_badges",
            {"project_dir": str(tmp_path)},
        )
        data = json.loads(result.data)

        assert data["project_name"] == "badge-project"
        assert data["badge_count"] >= 3  # CI, PyPI, Python, License
        labels = [b["label"] for b in data["badges"]]
        assert "CI" in labels
        assert "License" in labels

    async def test_badges_no_repo_url(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test badge generation with no repository URL returns only license badge."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "no-url-project"
version = "1.0.0"
license = "MIT"

[tool.poetry.dependencies]
python = "^3.11"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
        )

        result = await mcp_client.call_tool(
            "generate_badges",
            {"project_dir": str(tmp_path)},
        )
        data = json.loads(result.data)

        assert data["badge_count"] == 1
        assert data["badges"][0]["label"] == "License"

    async def test_badges_empty_project(self, mcp_client: Client, tmp_path: Path) -> None:
        """Test badge generation with minimal project returns empty list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.poetry]
name = "minimal-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
        )

        result = await mcp_client.call_tool(
            "generate_badges",
            {"project_dir": str(tmp_path)},
        )
        data = json.loads(result.data)

        assert data["badge_count"] == 0
        assert data["badges"] == []
