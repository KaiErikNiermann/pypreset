"""Utilities for reading, writing, and validating pyproject.toml metadata."""

from __future__ import annotations

import logging
import tomllib
from typing import TYPE_CHECKING, Any

import tomli_w

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Standard PyPI URL keys for [project.urls] / [tool.poetry.urls]
_URL_KEY_MAP = {
    "repository_url": "Repository",
    "homepage_url": "Homepage",
    "documentation_url": "Documentation",
    "bug_tracker_url": "Bug Tracker",
}


def read_pyproject_metadata(project_dir: Path) -> dict[str, Any]:
    """Read metadata from an existing pyproject.toml.

    Returns a flat dict with keys matching the Metadata model fields.
    Works with both Poetry ([tool.poetry]) and PEP 621 ([project]) layouts.
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"No pyproject.toml found in {project_dir}")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    # Detect layout
    if "tool" in data and "poetry" in data["tool"]:
        return _read_poetry_metadata(data)
    if "project" in data:
        return _read_pep621_metadata(data)

    raise ValueError("pyproject.toml has neither [tool.poetry] nor [project] section")


def _read_poetry_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from Poetry-style pyproject.toml."""
    poetry = data.get("tool", {}).get("poetry", {})
    urls = poetry.get("urls", {})

    return {
        "name": poetry.get("name", ""),
        "version": poetry.get("version", "0.1.0"),
        "description": poetry.get("description", ""),
        "authors": poetry.get("authors", []),
        "license": poetry.get("license"),
        "readme": poetry.get("readme", "README.md"),
        "keywords": poetry.get("keywords", []),
        "classifiers": poetry.get("classifiers", []),
        "repository_url": urls.get("Repository"),
        "homepage_url": urls.get("Homepage"),
        "documentation_url": urls.get("Documentation"),
        "bug_tracker_url": urls.get("Bug Tracker"),
    }


def _read_pep621_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from PEP 621-style pyproject.toml."""
    project = data.get("project", {})
    urls = project.get("urls", {})

    # PEP 621 authors are [{name=..., email=...}]
    raw_authors = project.get("authors", [])
    authors = []
    for a in raw_authors:
        name = a.get("name", "")
        email = a.get("email", "")
        authors.append(f"{name} <{email}>" if email else name)

    return {
        "name": project.get("name", ""),
        "version": project.get("version", "0.1.0"),
        "description": project.get("description", ""),
        "authors": authors,
        "license": project.get("license"),
        "readme": project.get("readme", "README.md"),
        "keywords": project.get("keywords", []),
        "classifiers": project.get("classifiers", []),
        "repository_url": urls.get("Repository"),
        "homepage_url": urls.get("Homepage"),
        "documentation_url": urls.get("Documentation"),
        "bug_tracker_url": urls.get("Bug Tracker"),
    }


def set_pyproject_metadata(
    project_dir: Path,
    updates: dict[str, Any],
    *,
    overwrite: bool = False,
) -> list[str]:
    """Update metadata fields in an existing pyproject.toml.

    Args:
        project_dir: Path to the project directory.
        updates: Dict of metadata field names to values.
        overwrite: If True, overwrite existing non-empty values.
                   If False, only set fields that are currently empty/unset.

    Returns:
        List of warnings about fields that remain empty.
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"No pyproject.toml found in {project_dir}")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    if "tool" in data and "poetry" in data["tool"]:
        warnings = _set_poetry_metadata(data, updates, overwrite=overwrite)
    elif "project" in data:
        warnings = _set_pep621_metadata(data, updates, overwrite=overwrite)
    else:
        raise ValueError("pyproject.toml has neither [tool.poetry] nor [project] section")

    with open(pyproject_path, "wb") as f:
        tomli_w.dump(data, f)

    return warnings


# Known placeholder/default values that should be treated as "empty"
_PLACEHOLDER_VALUES = {
    "A Python package",
    "",
}

_PLACEHOLDER_AUTHORS = {
    "Your Name <you@example.com>",
}


def _should_update(current_value: Any, overwrite: bool) -> bool:
    """Check if a field should be updated based on its current value."""
    if overwrite:
        return True
    if current_value is None:
        return True
    if isinstance(current_value, str) and current_value in _PLACEHOLDER_VALUES:
        return True
    if isinstance(current_value, list) and not current_value:
        return True
    return (
        isinstance(current_value, list)
        and len(current_value) == 1
        and current_value[0] in _PLACEHOLDER_AUTHORS
    )


def _set_poetry_metadata(
    data: dict[str, Any], updates: dict[str, Any], *, overwrite: bool
) -> list[str]:
    """Apply metadata updates to Poetry-style pyproject.toml."""
    poetry = data.setdefault("tool", {}).setdefault("poetry", {})

    _scalar_fields = ["name", "version", "description", "license", "readme"]
    _list_fields = ["authors", "keywords", "classifiers"]

    for field in _scalar_fields:
        if field in updates and _should_update(poetry.get(field), overwrite):
            poetry[field] = updates[field]

    for field in _list_fields:
        if field in updates and _should_update(poetry.get(field), overwrite):
            poetry[field] = updates[field]

    # URL fields → [tool.poetry.urls]
    url_updates = {
        display_key: updates[field]
        for field, display_key in _URL_KEY_MAP.items()
        if field in updates and updates[field]
    }
    if url_updates:
        urls = poetry.setdefault("urls", {})
        for display_key, value in url_updates.items():
            if _should_update(urls.get(display_key), overwrite):
                urls[display_key] = value

    return check_publish_readiness(data)


def _set_pep621_metadata(
    data: dict[str, Any], updates: dict[str, Any], *, overwrite: bool
) -> list[str]:
    """Apply metadata updates to PEP 621-style pyproject.toml."""
    project = data.setdefault("project", {})

    _scalar_fields = ["name", "version", "description", "license", "readme"]

    for field in _scalar_fields:
        if field in updates and _should_update(project.get(field), overwrite):
            project[field] = updates[field]

    # authors: convert from "Name <email>" to [{name=..., email=...}]
    if "authors" in updates and _should_update(project.get("authors"), overwrite):
        pep_authors = []
        for author in updates["authors"]:
            if "<" in author:
                name_part = author.split("<")[0].strip()
                email_part = author.split("<")[1].replace(">", "").strip()
                pep_authors.append({"name": name_part, "email": email_part})
            else:
                pep_authors.append({"name": author})
        project["authors"] = pep_authors

    # keywords / classifiers
    for field in ("keywords", "classifiers"):
        if field in updates and _should_update(project.get(field), overwrite):
            project[field] = updates[field]

    # URL fields → [project.urls]
    url_updates = {
        display_key: updates[field]
        for field, display_key in _URL_KEY_MAP.items()
        if field in updates and updates[field]
    }
    if url_updates:
        urls = project.setdefault("urls", {})
        for display_key, value in url_updates.items():
            if _should_update(urls.get(display_key), overwrite):
                urls[display_key] = value

    return check_publish_readiness(data)


def check_publish_readiness(data: dict[str, Any]) -> list[str]:
    """Check if metadata is sufficient for PyPI publishing.

    Returns a list of warning strings for empty/default fields.
    """
    # Read back via the appropriate reader
    if "tool" in data and "poetry" in data.get("tool", {}):
        meta = _read_poetry_metadata(data)
    elif "project" in data:
        meta = _read_pep621_metadata(data)
    else:
        return ["Could not detect pyproject.toml format"]

    warnings: list[str] = []

    if not meta.get("description"):
        warnings.append("'description' is empty - add a short package summary before publishing")
    elif meta["description"] in ("A Python package", ""):
        warnings.append("'description' is still the default - update it before publishing")

    if not meta.get("authors") or meta["authors"] == ["Your Name <you@example.com>"]:
        warnings.append(
            "'authors' is empty or placeholder - set real author info before publishing"
        )

    if not meta.get("license"):
        warnings.append("'license' is not set - consider adding a license (e.g. 'MIT')")

    if not meta.get("keywords"):
        warnings.append("'keywords' is empty - adding keywords improves PyPI discoverability")

    if not meta.get("repository_url"):
        warnings.append("'repository_url' is not set - link your source repository for users")

    return warnings


def generate_default_urls(project_name: str, github_owner: str | None = None) -> dict[str, str]:
    """Generate sensible default URLs from the project name and optional GitHub owner.

    If github_owner is provided, generates GitHub-based URLs.
    """
    urls: dict[str, str] = {}
    if github_owner:
        base = f"https://github.com/{github_owner}/{project_name}"
        urls["repository_url"] = base
        urls["homepage_url"] = base
        urls["bug_tracker_url"] = f"{base}/issues"
    return urls
