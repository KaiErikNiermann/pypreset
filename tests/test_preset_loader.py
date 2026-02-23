"""Tests for preset loading functionality."""

from pathlib import Path

import pytest

from pysetup.models import OverrideOptions
from pysetup.preset_loader import (
    build_project_config,
    deep_merge,
    find_preset_file,
    list_available_presets,
    load_preset,
    resolve_preset_chain,
)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_simple_merge(self) -> None:
        """Test merging simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 10, "z": 20}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 10, "z": 20}, "b": 3}

    def test_list_extension(self) -> None:
        """Test that lists are extended, not replaced."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = deep_merge(base, override)
        assert result == {"items": [1, 2, 3, 4, 5]}


class TestFindPresetFile:
    """Tests for find_preset_file function."""

    def test_find_builtin_preset(self) -> None:
        """Test finding a built-in preset."""
        preset_path = find_preset_file("empty-package")
        assert preset_path is not None
        assert preset_path.exists()
        assert preset_path.name == "empty-package.yaml"

    def test_find_nonexistent_preset(self) -> None:
        """Test finding a non-existent preset."""
        preset_path = find_preset_file("nonexistent-preset")
        assert preset_path is None

    def test_find_custom_preset(self, tmp_path: Path) -> None:
        """Test finding a custom preset file."""
        custom_preset = tmp_path / "custom.yaml"
        custom_preset.write_text("name: custom\ndescription: Custom preset")

        preset_path = find_preset_file("custom", custom_preset)
        assert preset_path == custom_preset


class TestListAvailablePresets:
    """Tests for list_available_presets function."""

    def test_lists_builtin_presets(self) -> None:
        """Test that built-in presets are listed."""
        presets = list_available_presets()
        preset_names = [name for name, _ in presets]

        assert "empty-package" in preset_names
        assert "cli-tool" in preset_names
        assert "discord-bot" in preset_names
        assert "data-science" in preset_names


class TestLoadPreset:
    """Tests for load_preset function."""

    def test_load_empty_package(self) -> None:
        """Test loading the empty-package preset."""
        preset = load_preset("empty-package")
        assert preset.name == "empty-package"
        assert preset.base is None

    def test_load_cli_tool(self) -> None:
        """Test loading the cli-tool preset."""
        preset = load_preset("cli-tool")
        assert preset.name == "cli-tool"
        assert preset.base == "empty-package"

    def test_load_nonexistent_raises(self) -> None:
        """Test that loading a non-existent preset raises an error."""
        with pytest.raises(ValueError, match="not found"):
            load_preset("nonexistent-preset")


class TestResolvePresetChain:
    """Tests for resolve_preset_chain function."""

    def test_resolve_simple_preset(self) -> None:
        """Test resolving a preset without inheritance."""
        preset = load_preset("empty-package")
        config = resolve_preset_chain(preset)

        assert "testing" in config
        assert config["testing"]["enabled"] is True

    def test_resolve_inherited_preset(self) -> None:
        """Test resolving a preset with inheritance."""
        preset = load_preset("cli-tool")
        config = resolve_preset_chain(preset)

        # Should have base preset's testing config
        assert config["testing"]["enabled"] is True

        # Should have cli-tool's entry points
        assert len(config["entry_points"]) > 0


class TestBuildProjectConfig:
    """Tests for build_project_config function."""

    def test_build_empty_package(self) -> None:
        """Test building config for empty-package preset."""
        config = build_project_config(
            project_name="my-test-project",
            preset_name="empty-package",
        )

        assert config.metadata.name == "my-test-project"
        assert config.testing.enabled is True
        assert config.formatting.enabled is True

    def test_build_with_overrides(self) -> None:
        """Test building config with overrides."""
        overrides = OverrideOptions(
            testing_enabled=False,
            python_version="3.12",
            extra_packages=["requests"],
        )

        config = build_project_config(
            project_name="my-project",
            preset_name="empty-package",
            overrides=overrides,
        )

        assert config.testing.enabled is False
        assert config.metadata.python_version == "3.12"
        assert "requests" in config.dependencies.main

    def test_build_cli_tool(self) -> None:
        """Test building config for cli-tool preset."""
        config = build_project_config(
            project_name="my-cli",
            preset_name="cli-tool",
        )

        assert config.metadata.name == "my-cli"
        assert len(config.entry_points) > 0
        assert any("typer" in pkg.lower() for pkg in config.dependencies.main)

    def test_build_data_science(self) -> None:
        """Test building config for data-science preset."""
        config = build_project_config(
            project_name="my-analysis",
            preset_name="data-science",
        )

        assert config.metadata.name == "my-analysis"
        assert any("pandas" in pkg.lower() for pkg in config.dependencies.main)
        assert len(config.structure.directories) > 0
