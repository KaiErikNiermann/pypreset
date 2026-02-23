"""Tests for CLI interface."""

from pathlib import Path

from typer.testing import CliRunner

from pypreset.cli import app

runner = CliRunner()


class TestCreateCommand:
    """Tests for the create command."""

    def test_create_with_default_preset(self, tmp_path: Path) -> None:
        """Test creating a project with default preset."""
        result = runner.invoke(
            app,
            ["create", "test-project", "--output", str(tmp_path), "--no-git"],
        )

        assert result.exit_code == 0
        assert "successfully" in result.stdout.lower() or "success" in result.stdout.lower()
        assert (tmp_path / "test-project").exists()

    def test_create_with_cli_preset(self, tmp_path: Path) -> None:
        """Test creating a project with cli-tool preset."""
        result = runner.invoke(
            app,
            ["create", "my-cli", "--preset", "cli-tool", "--output", str(tmp_path), "--no-git"],
        )

        assert result.exit_code == 0
        assert (tmp_path / "my-cli").exists()
        assert (tmp_path / "my-cli" / "src" / "my_cli" / "cli.py").exists()

    def test_create_with_data_science_preset(self, tmp_path: Path) -> None:
        """Test creating a project with data-science preset."""
        result = runner.invoke(
            app,
            [
                "create",
                "analysis",
                "--preset",
                "data-science",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        project_dir = tmp_path / "analysis"
        assert project_dir.exists()
        assert (project_dir / "data" / "raw").exists()
        assert (project_dir / "notebooks").exists()

    def test_create_with_discord_bot_preset(self, tmp_path: Path) -> None:
        """Test creating a project with discord-bot preset."""
        result = runner.invoke(
            app,
            ["create", "my-bot", "--preset", "discord-bot", "--output", str(tmp_path), "--no-git"],
        )

        assert result.exit_code == 0
        project_dir = tmp_path / "my-bot"
        assert project_dir.exists()
        assert (project_dir / "src" / "my_bot" / "bot.py").exists()

    def test_create_with_no_testing(self, tmp_path: Path) -> None:
        """Test creating a project with testing disabled."""
        result = runner.invoke(
            app,
            ["create", "no-tests", "--no-testing", "--output", str(tmp_path), "--no-git"],
        )

        assert result.exit_code == 0
        project_dir = tmp_path / "no-tests"
        assert project_dir.exists()
        assert not (project_dir / "tests").exists()

    def test_create_with_extra_packages(self, tmp_path: Path) -> None:
        """Test creating a project with extra packages."""
        result = runner.invoke(
            app,
            [
                "create",
                "extras",
                "--extra-package",
                "requests",
                "--extra-package",
                "httpx",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        project_dir = tmp_path / "extras"
        pyproject = project_dir / "pyproject.toml"
        content = pyproject.read_text()
        assert "requests" in content or "httpx" in content

    def test_create_with_invalid_preset(self, tmp_path: Path) -> None:
        """Test creating a project with invalid preset."""
        result = runner.invoke(
            app,
            ["create", "test", "--preset", "nonexistent", "--output", str(tmp_path)],
        )

        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestCreateFlatLayout:
    """Tests for creating projects with flat layout."""

    def test_create_flat_layout_project(self, tmp_path: Path) -> None:
        """Test creating a project with flat layout."""
        result = runner.invoke(
            app,
            [
                "create",
                "flat-proj",
                "--layout",
                "flat",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        project_dir = tmp_path / "flat-proj"
        assert project_dir.exists()
        # Flat layout: package at top level, no src/
        assert (project_dir / "flat_proj" / "__init__.py").exists()
        assert not (project_dir / "src").exists()

    def test_create_flat_layout_pyproject_has_no_from_src(self, tmp_path: Path) -> None:
        """Test that flat layout pyproject.toml doesn't use 'from = src'."""
        runner.invoke(
            app,
            [
                "create",
                "flat-pkg",
                "--layout",
                "flat",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "flat-pkg" / "pyproject.toml").read_text()
        assert 'from = "src"' not in pyproject
        assert "flat_pkg" in pyproject

    def test_create_src_layout_is_default(self, tmp_path: Path) -> None:
        """Test that src layout is the default."""
        runner.invoke(
            app,
            ["create", "src-proj", "--output", str(tmp_path), "--no-git"],
        )

        project_dir = tmp_path / "src-proj"
        assert (project_dir / "src" / "src_proj" / "__init__.py").exists()

    def test_validate_flat_layout_project(self, tmp_path: Path) -> None:
        """Test that validation passes for flat layout projects."""
        runner.invoke(
            app,
            [
                "create",
                "flat-valid",
                "--layout",
                "flat",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        result = runner.invoke(
            app,
            ["validate", str(tmp_path / "flat-valid")],
        )
        assert result.exit_code == 0
        assert "passed" in result.stdout.lower()


class TestCreateWithVersionBumping:
    """Tests for creating projects with bump-my-version."""

    def test_bump_my_version_flag_adds_config(self, tmp_path: Path) -> None:
        """Test that --bump-my-version adds bumpversion config to pyproject.toml."""
        result = runner.invoke(
            app,
            [
                "create",
                "bump-proj",
                "--bump-my-version",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        pyproject = (tmp_path / "bump-proj" / "pyproject.toml").read_text()
        assert "[tool.bumpversion]" in pyproject
        assert 'current_version = "0.1.0"' in pyproject
        assert "bump-my-version" in pyproject

    def test_bump_my_version_targets_src_layout(self, tmp_path: Path) -> None:
        """Test bumpversion file targets use src layout path."""
        runner.invoke(
            app,
            [
                "create",
                "bump-src",
                "--bump-my-version",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "bump-src" / "pyproject.toml").read_text()
        assert "src/bump_src/__init__.py" in pyproject

    def test_bump_my_version_targets_flat_layout(self, tmp_path: Path) -> None:
        """Test bumpversion file targets use flat layout path."""
        runner.invoke(
            app,
            [
                "create",
                "bump-flat",
                "--bump-my-version",
                "--layout",
                "flat",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "bump-flat" / "pyproject.toml").read_text()
        assert "bump_flat/__init__.py" in pyproject
        assert "src/" not in pyproject.split("[tool.bumpversion]")[1].split("[[tool.bumpversion")[1]

    def test_no_bump_my_version_by_default(self, tmp_path: Path) -> None:
        """Test that bump-my-version is not included by default."""
        runner.invoke(
            app,
            ["create", "no-bump", "--output", str(tmp_path), "--no-git"],
        )

        pyproject = (tmp_path / "no-bump" / "pyproject.toml").read_text()
        assert "[tool.bumpversion]" not in pyproject
        assert "bump-my-version" not in pyproject


class TestCreateWithTypeChecker:
    """Tests for creating projects with different type checkers."""

    def test_default_uses_mypy(self, tmp_path: Path) -> None:
        """Test that mypy is the default type checker."""
        runner.invoke(
            app,
            ["create", "mypy-proj", "--output", str(tmp_path), "--no-git"],
        )

        pyproject = (tmp_path / "mypy-proj" / "pyproject.toml").read_text()
        assert "[tool.mypy]" in pyproject
        assert 'mypy = "^1.13.0"' in pyproject

    def test_ty_type_checker(self, tmp_path: Path) -> None:
        """Test that --type-checker ty uses ty instead of mypy."""
        result = runner.invoke(
            app,
            [
                "create",
                "ty-proj",
                "--type-checker",
                "ty",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        pyproject = (tmp_path / "ty-proj" / "pyproject.toml").read_text()
        assert "[tool.ty]" in pyproject
        assert 'ty = "' in pyproject
        assert "[tool.mypy]" not in pyproject
        assert 'mypy = "' not in pyproject

    def test_pyright_type_checker(self, tmp_path: Path) -> None:
        """Test that --type-checker pyright uses pyright instead of mypy."""
        result = runner.invoke(
            app,
            [
                "create",
                "pyright-proj",
                "--type-checker",
                "pyright",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        pyproject = (tmp_path / "pyright-proj" / "pyproject.toml").read_text()
        assert "[tool.pyright]" in pyproject
        assert 'pyright = "' in pyproject
        assert "[tool.mypy]" not in pyproject
        assert "[tool.ty]" not in pyproject

    def test_pyright_strict_mode(self, tmp_path: Path) -> None:
        """Test that pyright with strict typing uses strict mode."""
        runner.invoke(
            app,
            [
                "create",
                "pyright-strict",
                "--type-checker",
                "pyright",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "pyright-strict" / "pyproject.toml").read_text()
        assert 'typeCheckingMode = "strict"' in pyproject

    def test_none_type_checker_with_strict_typing(self, tmp_path: Path) -> None:
        """Test that --type-checker none omits type checker even with strict typing."""
        runner.invoke(
            app,
            [
                "create",
                "no-tc",
                "--type-checker",
                "none",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "no-tc" / "pyproject.toml").read_text()
        assert "[tool.mypy]" not in pyproject
        assert "[tool.pyright]" not in pyproject
        assert "[tool.ty]" not in pyproject

    def test_ty_in_ci_workflow(self, tmp_path: Path) -> None:
        """Test that ty type checker appears in CI workflow."""
        runner.invoke(
            app,
            [
                "create",
                "ty-ci",
                "--type-checker",
                "ty",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        ci_path = tmp_path / "ty-ci" / ".github" / "workflows" / "ci.yaml"
        ci_content = ci_path.read_text()
        assert "ty check" in ci_content
        assert "mypy" not in ci_content

    def test_pyright_in_ci_workflow(self, tmp_path: Path) -> None:
        """Test that pyright type checker appears in CI workflow."""
        runner.invoke(
            app,
            [
                "create",
                "pyright-ci",
                "--type-checker",
                "pyright",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        ci_path = tmp_path / "pyright-ci" / ".github" / "workflows" / "ci.yaml"
        ci_content = ci_path.read_text()
        assert "pyright src" in ci_content
        assert "mypy" not in ci_content
        assert "ty check" not in ci_content


class TestCreateWithUv:
    """Tests for creating projects with uv package manager."""

    def test_uv_project_uses_pep621_metadata(self, tmp_path: Path) -> None:
        """Test that uv projects use [project] instead of [tool.poetry]."""
        result = runner.invoke(
            app,
            [
                "create",
                "uv-proj",
                "--package-manager",
                "uv",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        assert result.exit_code == 0
        pyproject = (tmp_path / "uv-proj" / "pyproject.toml").read_text()
        assert "[project]" in pyproject
        assert "[tool.poetry]" not in pyproject
        assert "hatchling" in pyproject

    def test_uv_project_uses_dependency_groups(self, tmp_path: Path) -> None:
        """Test that uv projects use [dependency-groups] for dev deps."""
        runner.invoke(
            app,
            [
                "create",
                "uv-deps",
                "--package-manager",
                "uv",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "uv-deps" / "pyproject.toml").read_text()
        assert "[dependency-groups]" in pyproject
        assert '"pytest>=' in pyproject

    def test_uv_ci_workflow_uses_uv_commands(self, tmp_path: Path) -> None:
        """Test that uv CI workflow uses uv run/sync commands."""
        runner.invoke(
            app,
            [
                "create",
                "uv-ci",
                "--package-manager",
                "uv",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        ci_path = tmp_path / "uv-ci" / ".github" / "workflows" / "ci.yaml"
        ci_content = ci_path.read_text()
        assert "uv sync" in ci_content
        assert "uv run" in ci_content
        assert "astral-sh/setup-uv" in ci_content
        assert "poetry" not in ci_content.lower()

    def test_default_is_poetry(self, tmp_path: Path) -> None:
        """Test that the default package manager is poetry."""
        runner.invoke(
            app,
            ["create", "default-pm", "--output", str(tmp_path), "--no-git"],
        )

        pyproject = (tmp_path / "default-pm" / "pyproject.toml").read_text()
        assert "[tool.poetry]" in pyproject

    def test_uv_src_layout(self, tmp_path: Path) -> None:
        """Test uv project with src layout has hatch build config."""
        runner.invoke(
            app,
            [
                "create",
                "uv-src",
                "--package-manager",
                "uv",
                "--output",
                str(tmp_path),
                "--no-git",
            ],
        )

        pyproject = (tmp_path / "uv-src" / "pyproject.toml").read_text()
        assert "[tool.hatch.build.targets.wheel]" in pyproject
        assert 'packages = ["src/uv_src"]' in pyproject


class TestListPresetsCommand:
    """Tests for the list-presets command."""

    def test_list_presets(self) -> None:
        """Test listing available presets."""
        result = runner.invoke(app, ["list-presets"])

        assert result.exit_code == 0
        assert "empty-package" in result.stdout
        assert "cli-tool" in result.stdout
        assert "data-science" in result.stdout
        assert "discord-bot" in result.stdout


class TestShowPresetCommand:
    """Tests for the show-preset command."""

    def test_show_empty_package(self) -> None:
        """Test showing empty-package preset details."""
        result = runner.invoke(app, ["show-preset", "empty-package"])

        assert result.exit_code == 0
        assert "empty-package" in result.stdout

    def test_show_cli_tool(self) -> None:
        """Test showing cli-tool preset details."""
        result = runner.invoke(app, ["show-preset", "cli-tool"])

        assert result.exit_code == 0
        assert "typer" in result.stdout.lower()

    def test_show_nonexistent_preset(self) -> None:
        """Test showing non-existent preset."""
        result = runner.invoke(app, ["show-preset", "nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_project(self, tmp_path: Path) -> None:
        """Test validating a valid project."""
        # First create a project
        runner.invoke(
            app,
            ["create", "valid-project", "--output", str(tmp_path), "--no-git"],
        )

        # Then validate it
        result = runner.invoke(
            app,
            ["validate", str(tmp_path / "valid-project")],
        )

        assert result.exit_code == 0
        assert "passed" in result.stdout.lower()

    def test_validate_invalid_directory(self, tmp_path: Path) -> None:
        """Test validating a non-existent directory."""
        result = runner.invoke(
            app,
            ["validate", str(tmp_path / "nonexistent")],
        )

        assert result.exit_code != 0
