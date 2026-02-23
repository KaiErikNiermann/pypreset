"""Preset loading and merging functionality."""

import logging
from pathlib import Path
from typing import Any

import yaml

from pypreset.models import (
    CreationPackageManager,
    DependabotConfig,
    Dependencies,
    DirectoryStructure,
    EntryPoint,
    FileTemplate,
    FormattingConfig,
    LayoutStyle,
    Metadata,
    OverrideOptions,
    PresetConfig,
    ProjectConfig,
    TestingConfig,
    TypingLevel,
)
from pypreset.user_config import apply_user_defaults

logger = logging.getLogger(__name__)


def get_builtin_presets_dir() -> Path:
    """Get the directory containing built-in presets."""
    return Path(__file__).parent / "presets"


def get_user_presets_dir() -> Path:
    """Get the user's custom presets directory."""
    return Path.home() / ".config" / "pypreset" / "presets"


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    None values in override are skipped (treated as "not set").
    """
    result = base.copy()
    for key, value in override.items():
        # Skip None values (they mean "not set" in partial configs)
        if value is None:
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)  # type: ignore[arg-type]
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists, extend rather than replace
            result[key] = result[key] + value
        else:
            result[key] = value
    return result


def find_preset_file(preset_name: str, custom_path: Path | None = None) -> Path | None:
    """Find a preset file by name."""
    if custom_path and custom_path.exists():
        return custom_path

    # Check user presets first
    user_preset = get_user_presets_dir() / f"{preset_name}.yaml"
    if user_preset.exists():
        return user_preset

    # Check built-in presets
    builtin_preset = get_builtin_presets_dir() / f"{preset_name}.yaml"
    if builtin_preset.exists():
        return builtin_preset

    return None


def list_available_presets() -> list[tuple[str, str]]:
    """List all available presets with their descriptions."""
    presets: list[tuple[str, str]] = []
    seen_names: set[str] = set()

    # Check user presets first (they take precedence)
    user_dir = get_user_presets_dir()
    if user_dir.exists():
        for preset_file in user_dir.glob("*.yaml"):
            name = preset_file.stem
            if name not in seen_names:
                data = load_yaml_file(preset_file)
                description = data.get("description", "")
                presets.append((name, f"{description} (user)"))
                seen_names.add(name)

    # Check built-in presets
    builtin_dir = get_builtin_presets_dir()
    if builtin_dir.exists():
        for preset_file in builtin_dir.glob("*.yaml"):
            name = preset_file.stem
            if name not in seen_names:
                data = load_yaml_file(preset_file)
                description = data.get("description", "")
                presets.append((name, description))
                seen_names.add(name)

    return sorted(presets, key=lambda x: x[0])


def load_preset(preset_name: str, custom_path: Path | None = None) -> PresetConfig:
    """Load a preset configuration."""
    preset_path = find_preset_file(preset_name, custom_path)
    if preset_path is None:
        raise ValueError(f"Preset '{preset_name}' not found")

    data = load_yaml_file(preset_path)
    return PresetConfig(**data)


def resolve_preset_chain(preset: PresetConfig) -> dict[str, Any]:
    """Resolve a preset's inheritance chain and return merged config."""
    if preset.base is None:
        return preset.model_dump(exclude={"name", "description", "base"})

    # Load and resolve base preset
    base_preset = load_preset(preset.base)
    base_config = resolve_preset_chain(base_preset)

    # Merge current preset on top
    current_config = preset.model_dump(exclude={"name", "description", "base"})
    return deep_merge(base_config, current_config)


def _set_nested(config: dict[str, Any], section: str, key: str, value: Any) -> None:
    """Set a value in a nested config section, creating the section if needed."""
    if section not in config:
        config[section] = {}
    config[section][key] = value


def _extend_dep_list(config: dict[str, Any], group: str, packages: list[str]) -> None:
    """Extend a dependency list, creating the structure if needed."""
    deps = config.setdefault("dependencies", {})
    deps.setdefault(group, []).extend(packages)


def apply_overrides(config: dict[str, Any], overrides: OverrideOptions) -> dict[str, Any]:
    """Apply runtime overrides to a configuration."""
    result = config.copy()

    # Nested overrides: (value, section, key) — applied when value is not None
    _nested_overrides: list[tuple[Any, str, str]] = [
        (overrides.testing_enabled, "testing", "enabled"),
        (overrides.formatting_enabled, "formatting", "enabled"),
        (overrides.radon_enabled, "formatting", "radon"),
        (overrides.pre_commit_enabled, "formatting", "pre_commit"),
        (overrides.version_bumping_enabled, "formatting", "version_bumping"),
        (overrides.python_version, "metadata", "python_version"),
    ]
    for value, section, key in _nested_overrides:
        if value is not None:
            _set_nested(result, section, key, value)

    # Enum overrides stored via .value
    if overrides.type_checker is not None:
        _set_nested(result, "formatting", "type_checker", overrides.type_checker.value)

    # Top-level enum overrides
    if overrides.typing_level is not None:
        result["typing_level"] = overrides.typing_level.value
    if overrides.layout is not None:
        result["layout"] = overrides.layout.value
    if overrides.package_manager is not None:
        result["package_manager"] = overrides.package_manager.value

    # Dependency list extensions
    if overrides.extra_packages:
        _extend_dep_list(result, "main", overrides.extra_packages)
    if overrides.extra_dev_packages:
        _extend_dep_list(result, "dev", overrides.extra_dev_packages)

    return result


def build_project_config(
    project_name: str,
    preset_name: str,
    overrides: OverrideOptions | None = None,
    custom_preset_path: Path | None = None,
) -> ProjectConfig:
    """Build a complete project configuration from a preset and overrides."""
    # Load and resolve the preset
    preset = load_preset(preset_name, custom_preset_path)
    config = resolve_preset_chain(preset)

    # Apply user-level defaults (lowest priority — presets override these)
    config = apply_user_defaults(config)

    # Apply runtime overrides (highest priority)
    if overrides:
        config = apply_overrides(config, overrides)

    # Set the project name in metadata
    if "metadata" not in config:
        config["metadata"] = {}
    config["metadata"]["name"] = project_name

    # Replace placeholders in entry points
    package_name = project_name.replace("-", "_")
    config = _replace_placeholders(config, project_name, package_name)

    # Convert to ProjectConfig
    return _dict_to_project_config(config)


def _replace_placeholders(
    config: dict[str, Any], project_name: str, package_name: str
) -> dict[str, Any]:
    """Replace __PROJECT_NAME__ and __PACKAGE_NAME__ placeholders in config."""
    result = config.copy()

    # Replace in entry points
    if "entry_points" in result:
        new_entry_points = []
        for ep in result["entry_points"]:
            new_ep = {}
            for key, value in ep.items():
                if isinstance(value, str):
                    value = value.replace("__PROJECT_NAME__", project_name)
                    value = value.replace("__PACKAGE_NAME__", package_name)
                new_ep[key] = value
            new_entry_points.append(new_ep)
        result["entry_points"] = new_entry_points

    return result


def _strip_none_values(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively strip None values from a dictionary."""
    result = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            result[key] = _strip_none_values(value)
        else:
            result[key] = value
    return result


def _dict_to_project_config(data: dict[str, Any]) -> ProjectConfig:
    """Convert a dictionary to a ProjectConfig object."""
    # Strip None values from the entire config
    data = _strip_none_values(data)

    # Build metadata
    metadata_data = data.get("metadata", {})
    metadata = Metadata(**metadata_data)

    # Build structure
    structure_data = data.get("structure", {})
    files = [FileTemplate(**f) for f in structure_data.get("files", [])]
    structure = DirectoryStructure(
        directories=structure_data.get("directories", []),
        files=files,
    )

    # Build dependencies
    deps_data = data.get("dependencies", {})
    dependencies = Dependencies(
        main=deps_data.get("main", []),
        dev=deps_data.get("dev", []),
        optional=deps_data.get("optional", {}),
    )

    # Build testing config
    testing_data = data.get("testing", {})
    testing = TestingConfig(**testing_data) if testing_data else TestingConfig()  # type: ignore[call-arg]

    # Build formatting config
    formatting_data = data.get("formatting", {})
    formatting = FormattingConfig(**formatting_data) if formatting_data else FormattingConfig()  # type: ignore[call-arg]

    # Build dependabot config
    dependabot_data = data.get("dependabot", {})
    dependabot = DependabotConfig(**dependabot_data) if dependabot_data else DependabotConfig()  # type: ignore[call-arg]

    # Build entry points
    entry_points = [EntryPoint(**ep) for ep in data.get("entry_points", [])]

    # Build typing level
    typing_level_str = data.get("typing_level", "strict")
    typing_level = TypingLevel(typing_level_str) if typing_level_str else TypingLevel.STRICT

    # Build layout style
    layout_str = data.get("layout", "src")
    layout = LayoutStyle(layout_str) if layout_str else LayoutStyle.SRC

    # Build package manager
    pm_str = data.get("package_manager", "poetry")
    package_manager = CreationPackageManager(pm_str) if pm_str else CreationPackageManager.POETRY

    return ProjectConfig(
        metadata=metadata,
        structure=structure,
        dependencies=dependencies,
        testing=testing,
        formatting=formatting,
        dependabot=dependabot,
        typing_level=typing_level,
        layout=layout,
        package_manager=package_manager,
        entry_points=entry_points,
        extras=data.get("extras", {}),
    )
