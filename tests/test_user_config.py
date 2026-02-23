"""Tests for user configuration system."""

from pathlib import Path
from unittest.mock import patch

import yaml

from pypreset.user_config import (
    apply_user_defaults,
    get_default_config_template,
    load_user_config,
    save_user_config,
)


class TestLoadUserConfig:
    """Tests for load_user_config."""

    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        """Missing config file returns empty dict."""
        with patch("pypreset.user_config.get_config_path", return_value=tmp_path / "nope.yaml"):
            assert load_user_config() == {}

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        """Valid YAML config is loaded correctly."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"python_version": "3.13", "layout": "flat"}))

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = load_user_config()

        assert result["python_version"] == "3.13"
        assert result["layout"] == "flat"

    def test_skips_invalid_enum_values(self, tmp_path: Path) -> None:
        """Invalid enum values are dropped with a warning."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"layout": "invalid_layout", "python_version": "3.12"}))

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = load_user_config()

        assert "layout" not in result
        assert result["python_version"] == "3.12"

    def test_handles_corrupt_yaml(self, tmp_path: Path) -> None:
        """Corrupt YAML returns empty dict."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text("this: is: not: valid: yaml: [")

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            assert load_user_config() == {}


class TestApplyUserDefaults:
    """Tests for apply_user_defaults."""

    def test_applies_python_version(self, tmp_path: Path) -> None:
        """User python_version is set as default in metadata."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"python_version": "3.13"}))

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = apply_user_defaults({})

        assert result["metadata"]["python_version"] == "3.13"

    def test_preset_overrides_user_default(self, tmp_path: Path) -> None:
        """Preset values take precedence over user defaults (setdefault)."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"python_version": "3.13"}))

        config = {"metadata": {"python_version": "3.11"}}
        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = apply_user_defaults(config)

        assert result["metadata"]["python_version"] == "3.11"

    def test_applies_layout(self, tmp_path: Path) -> None:
        """User layout preference is applied."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"layout": "flat"}))

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = apply_user_defaults({})

        assert result["layout"] == "flat"

    def test_applies_formatter(self, tmp_path: Path) -> None:
        """User formatter preference is applied."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"formatter": "black"}))

        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            result = apply_user_defaults({})

        assert result["formatting"]["tool"] == "black"

    def test_noop_when_no_config(self, tmp_path: Path) -> None:
        """No user config means input passes through unchanged."""
        with patch(
            "pypreset.user_config.get_config_path",
            return_value=tmp_path / "nope.yaml",
        ):
            config = {"metadata": {"name": "test"}}
            result = apply_user_defaults(config)

        assert result == config


class TestSaveUserConfig:
    """Tests for save_user_config."""

    def test_saves_and_loads_roundtrip(self, tmp_path: Path) -> None:
        """Config can be saved and loaded back."""
        cfg_path = tmp_path / "subdir" / "config.yaml"
        with patch("pypreset.user_config.get_config_path", return_value=cfg_path):
            save_user_config({"python_version": "3.14", "layout": "src"})
            result = load_user_config()

        assert result["python_version"] == "3.14"
        assert result["layout"] == "src"


class TestDefaultConfigTemplate:
    """Tests for get_default_config_template."""

    def test_template_has_expected_keys(self) -> None:
        """Default template contains all standard keys."""
        template = get_default_config_template()
        assert "python_version" in template
        assert "layout" in template
        assert "typing_level" in template
        assert "formatter" in template
        assert "line_length" in template
        assert "testing_framework" in template
