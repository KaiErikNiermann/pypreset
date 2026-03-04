#!/usr/bin/env python3
"""Check that installed dev tool versions match pyproject.toml specs.

Catches silent version drift where Poetry updates package metadata
without replacing the actual venv binary (e.g. stale ruff 0.8.6
passing local checks while CI installs fresh 0.15.4).

Usage:
    poetry run python scripts/check_tool_versions.py
"""

from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

# Tools checked by the pre-push hook
TOOLS_TO_CHECK = ["ruff", "pytest", "pyright", "radon"]


def _poetry_spec_to_pep440(spec: str) -> str:
    """Convert a Poetry version spec to a PEP 440 specifier string.

    Handles caret (^) and tilde (~) operators that Poetry uses but
    PEP 440 does not.

    Examples:
        ^0.15.2  -> >=0.15.2,<0.16.0
        ^1.1.408 -> >=1.1.408,<2.0.0
        ^9.0.2   -> >=9.0.2,<10.0.0
        ~6.0.1   -> >=6.0.1,<6.1.0
        >=1.0    -> >=1.0  (passthrough)
    """
    spec = spec.strip()

    if spec.startswith("^"):
        v = Version(spec[1:])
        parts = list(v.release)
        # Pad to at least 3 parts
        while len(parts) < 3:
            parts.append(0)

        # Caret: first non-zero part gets bumped
        if parts[0] != 0:
            upper = f"{parts[0] + 1}.0.0"
        elif parts[1] != 0:
            upper = f"0.{parts[1] + 1}.0"
        else:
            upper = f"0.0.{parts[2] + 1}"

        return f">={v},<{upper}"

    if spec.startswith("~"):
        v = Version(spec[1:])
        parts = list(v.release)
        while len(parts) < 3:
            parts.append(0)
        upper = f"{parts[0]}.{parts[1] + 1}.0"
        return f">={v},<{upper}"

    # Already PEP 440 — passthrough
    return spec


def _extract_version_spec(dep_value: object) -> str | None:
    """Extract version string from a pyproject.toml dependency value.

    Handles both simple strings ("^0.15.2") and table forms
    ({"version": "^0.15.2", "optional": true}).
    """
    if isinstance(dep_value, str):
        return dep_value
    if isinstance(dep_value, dict):
        return dep_value.get("version")
    return None


def check_versions(pyproject_path: Path | None = None) -> list[str]:
    """Check installed versions against pyproject.toml specs.

    Returns a list of mismatch descriptions (empty = all OK).
    """
    if pyproject_path is None:
        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Gather all dependency sections
    deps: dict[str, object] = {}
    poetry = pyproject.get("tool", {}).get("poetry", {})

    # Main dependencies
    deps.update(poetry.get("dependencies", {}))

    # Dev group dependencies
    for group in poetry.get("group", {}).values():
        deps.update(group.get("dependencies", {}))

    mismatches: list[str] = []

    for tool in TOOLS_TO_CHECK:
        if tool not in deps:
            continue

        raw_spec = _extract_version_spec(deps[tool])
        if raw_spec is None:
            continue

        pep440_spec = _poetry_spec_to_pep440(raw_spec)
        specifier = SpecifierSet(pep440_spec)

        try:
            installed = installed_version(tool)
        except PackageNotFoundError:
            mismatches.append(f"  {tool}: not installed (expected {raw_spec})")
            continue

        if Version(installed) not in specifier:
            mismatches.append(
                f"  {tool}: installed {installed} does not match spec {raw_spec} ({pep440_spec})"
            )

    return mismatches


def main() -> None:
    mismatches = check_versions()
    if mismatches:
        print("Version sync check FAILED — installed tools do not match pyproject.toml:\n")
        print("\n".join(mismatches))
        print("\nRun `poetry install --sync` to fix.")
        sys.exit(1)
    else:
        print(f"Version sync OK — {len(TOOLS_TO_CHECK)} tools match pyproject.toml specs.")


if __name__ == "__main__":
    main()
