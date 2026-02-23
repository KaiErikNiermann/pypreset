"""User-level configuration for pysetup defaults.

Reads from ~/.config/pysetup/config.yaml and provides defaults
that are applied during project creation and augmentation.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from pysetup.models import (
    CreationPackageManager,
    FormattingTool,
    LayoutStyle,
    TestingFramework,
    TypeChecker,
    TypingLevel,
)

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "pysetup"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Keys that map to enum types for validation
_ENUM_FIELDS: dict[str, type[Enum]] = {
    "layout": LayoutStyle,
    "typing_level": TypingLevel,
    "formatter": FormattingTool,
    "testing_framework": TestingFramework,
    "type_checker": TypeChecker,
    "package_manager": CreationPackageManager,
}


def get_config_path() -> Path:
    """Return the path to the user config file."""
    return CONFIG_FILE


def load_user_config() -> dict[str, Any]:
    """Load user configuration from disk.

    Returns an empty dict if the file doesn't exist or is invalid.
    """
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load user config from {config_path}: {e}")
        return {}

    if not isinstance(data, dict):
        logger.warning(f"User config is not a mapping: {config_path}")
        return {}

    # Validate enum fields
    validated: dict[str, Any] = {}
    for key, value in data.items():
        if key in _ENUM_FIELDS and value is not None:
            try:
                _ENUM_FIELDS[key](value)
            except ValueError:
                valid = [e.value for e in _ENUM_FIELDS[key]]
                logger.warning(
                    f"Invalid value '{value}' for '{key}' in user config. Valid: {valid}"
                )
                continue
        validated[key] = value

    return validated


def apply_user_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Apply user defaults to a project config dict.

    User defaults are applied as a base layer — preset values and CLI
    overrides take precedence (they are applied after this).
    """
    user_cfg = load_user_config()
    if not user_cfg:
        return config

    result = config.copy()

    # python_version → metadata.python_version
    if "python_version" in user_cfg:
        metadata = result.setdefault("metadata", {})
        metadata.setdefault("python_version", user_cfg["python_version"])

    # layout
    if "layout" in user_cfg:
        result.setdefault("layout", user_cfg["layout"])

    # typing_level
    if "typing_level" in user_cfg:
        result.setdefault("typing_level", user_cfg["typing_level"])

    # formatter → formatting.tool
    if "formatter" in user_cfg:
        formatting = result.setdefault("formatting", {})
        formatting.setdefault("tool", user_cfg["formatter"])

    # line_length → formatting.line_length
    if "line_length" in user_cfg:
        formatting = result.setdefault("formatting", {})
        formatting.setdefault("line_length", user_cfg["line_length"])

    # testing_framework → testing.framework
    if "testing_framework" in user_cfg:
        testing = result.setdefault("testing", {})
        testing.setdefault("framework", user_cfg["testing_framework"])

    # type_checker → formatting.type_checker
    if "type_checker" in user_cfg:
        formatting = result.setdefault("formatting", {})
        formatting.setdefault("type_checker", user_cfg["type_checker"])

    # package_manager
    if "package_manager" in user_cfg:
        result.setdefault("package_manager", user_cfg["package_manager"])

    return result


def save_user_config(config: dict[str, Any]) -> Path:
    """Save configuration to the user config file.

    Returns the path written to.
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    return config_path


def get_default_config_template() -> dict[str, Any]:
    """Return a commented example config for scaffolding."""
    return {
        "python_version": "3.12",
        "layout": "src",
        "typing_level": "strict",
        "formatter": "ruff",
        "line_length": 100,
        "testing_framework": "pytest",
        "type_checker": "mypy",
        "package_manager": "poetry",
    }
