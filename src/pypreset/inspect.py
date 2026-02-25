"""Project inspection utilities — tree structure and dependency extraction.

Standalone, tool-agnostic helpers that work on any Python project with a
``pyproject.toml`` (Poetry, uv/hatch, PDM, flit, setuptools) or
``requirements*.txt`` / ``Pipfile``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 — used at runtime
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

# Directories / files never shown in the tree output.
_IGNORED_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pyright",
        ".ruff_cache",
        ".pytest_cache",
        ".eggs",
        "*.egg-info",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "env",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }
)


# ── tree structure ────────────────────────────────────────────────────────


def _should_skip(name: str) -> bool:
    """Return ``True`` if *name* should be hidden in the tree."""
    if name.startswith("."):
        return True
    if name in _IGNORED_NAMES:
        return True
    # egg-info dirs
    return bool(name.endswith(".egg-info"))


def _build_tree_lines(
    root: Path,
    prefix: str,
    *,
    max_depth: int,
    current_depth: int,
) -> list[str]:
    """Recursively build tree-drawing lines."""
    if current_depth > max_depth:
        return []

    entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    visible = [e for e in entries if not _should_skip(e.name)]

    lines: list[str] = []
    for i, entry in enumerate(visible):
        is_last = i == len(visible) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir() and current_depth < max_depth:
            extension = "    " if is_last else "│   "
            lines.extend(
                _build_tree_lines(
                    entry,
                    prefix + extension,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
            )

    return lines


def project_tree(project_dir: Path, *, max_depth: int = 3) -> str:
    """Return a textual tree representation of *project_dir*.

    Hidden files/dirs (``.*``), caches, ``node_modules``, ``dist``, etc.
    are automatically excluded.

    Args:
        project_dir: Root directory to inspect.
        max_depth: How many directory levels deep to recurse (default 3).

    Returns:
        A multi-line string with the tree drawing (UTF-8 box characters).
    """
    project_dir = project_dir.resolve()
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {project_dir}")

    lines = [project_dir.name + "/"]
    lines.extend(_build_tree_lines(project_dir, "", max_depth=max_depth, current_depth=1))
    return "\n".join(lines)


# ── dependency extraction ─────────────────────────────────────────────────

_VERSION_RE = re.compile(
    r"""
    ^
    (?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)
    (?:\[(?P<extras>[^\]]*)\])?
    \s*
    (?P<version>.+)?
    $
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Dependency:
    """A single dependency with name and version constraint."""

    name: str
    version: str
    extras: list[str] = field(default_factory=list)
    group: str = "main"
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for JSON output)."""
        d: dict[str, Any] = {"name": self.name, "version": self.version, "group": self.group}
        if self.extras:
            d["extras"] = self.extras
        if self.source:
            d["source"] = self.source
        return d


def _parse_pep508(spec: str, *, group: str = "main", source: str = "") -> Dependency | None:
    """Parse a PEP 508 requirement string into a ``Dependency``."""
    spec = spec.strip()
    if not spec or spec.startswith("#"):
        return None

    # Strip environment markers (;python_version>="3.8" etc.)
    marker_idx = spec.find(";")
    if marker_idx != -1:
        spec = spec[:marker_idx].strip()

    m = _VERSION_RE.match(spec)
    if not m:
        return None

    name = m.group("name")
    extras_raw = m.group("extras") or ""
    extras = [e.strip() for e in extras_raw.split(",") if e.strip()] if extras_raw else []
    version = (m.group("version") or "").strip()
    # Normalise away leading commas / whitespace
    version = version.strip(",").strip() if version else "*"
    return Dependency(name=name, version=version, extras=extras, group=group, source=source)


def _poetry_version_to_str(value: Any) -> str:
    """Convert a Poetry dependency value to a human-readable version string."""
    match value:
        case str():
            return value or "*"
        case dict():
            return str(value.get("version", "*"))
        case _:
            return "*"


def _poetry_extras(value: Any) -> list[str]:
    """Extract extras from a Poetry dependency value."""
    if isinstance(value, dict):
        raw = value.get("extras", [])
        return list(raw) if isinstance(raw, list) else []
    return []


def extract_dependencies(project_dir: Path) -> list[Dependency]:
    """Extract all dependencies from a Python project directory.

    Supports:
    * Poetry (``[tool.poetry.dependencies]``, groups, ``dev-dependencies``)
    * PEP 621 (``[project.dependencies]``, ``optional-dependencies``,
      ``dependency-groups``)
    * ``requirements*.txt`` / ``requirements*.in`` files
    * ``Pipfile``

    Returns:
        A list of :class:`Dependency` objects sorted by (group, name).
    """
    project_dir = project_dir.resolve()
    deps: list[Dependency] = []

    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            logger.warning("Failed to parse pyproject.toml")
            data = {}

        deps.extend(_extract_poetry(data))
        deps.extend(_extract_pep621(data))
        deps.extend(_extract_dependency_groups(data))

    # requirements*.txt / *.in
    for pattern in ("requirements*.txt", "requirements*.in"):
        for req_file in sorted(project_dir.glob(pattern)):
            group = _group_from_requirements_filename(req_file.stem)
            deps.extend(_extract_requirements_file(req_file, group=group))

    # Pipfile
    pipfile = project_dir / "Pipfile"
    if pipfile.exists():
        deps.extend(_extract_pipfile(pipfile))

    # Deduplicate (prefer earlier source) then sort
    seen: set[tuple[str, str]] = set()
    unique: list[Dependency] = []
    for dep in deps:
        key = (dep.name.lower(), dep.group)
        if key not in seen:
            seen.add(key)
            unique.append(dep)

    return sorted(unique, key=lambda d: (d.group, d.name.lower()))


# ── extractors ────────────────────────────────────────────────────────────


def _extract_poetry(data: dict[str, Any]) -> list[Dependency]:
    poetry = data.get("tool", {}).get("poetry", {})
    if not poetry:
        return []

    deps: list[Dependency] = []
    src = "pyproject.toml [tool.poetry]"

    # Main deps
    for name, value in poetry.get("dependencies", {}).items():
        if name.lower() == "python":
            continue
        deps.append(
            Dependency(
                name=name,
                version=_poetry_version_to_str(value),
                extras=_poetry_extras(value),
                group="main",
                source=src,
            )
        )

    # Old-style dev-dependencies
    for name, value in poetry.get("dev-dependencies", {}).items():
        deps.append(
            Dependency(
                name=name,
                version=_poetry_version_to_str(value),
                extras=_poetry_extras(value),
                group="dev",
                source=src,
            )
        )

    # Poetry groups
    for group_name, group_data in poetry.get("group", {}).items():
        for name, value in group_data.get("dependencies", {}).items():
            deps.append(
                Dependency(
                    name=name,
                    version=_poetry_version_to_str(value),
                    extras=_poetry_extras(value),
                    group=group_name,
                    source=src,
                )
            )

    return deps


def _extract_pep621(data: dict[str, Any]) -> list[Dependency]:
    project = data.get("project", {})
    if not project:
        return []

    deps: list[Dependency] = []
    src = "pyproject.toml [project]"

    for spec in project.get("dependencies", []):
        dep = _parse_pep508(spec, group="main", source=src)
        if dep:
            deps.append(dep)

    for group_name, specs in project.get("optional-dependencies", {}).items():
        for spec in specs:
            dep = _parse_pep508(spec, group=group_name, source=src)
            if dep:
                deps.append(dep)

    return deps


def _extract_dependency_groups(data: dict[str, Any]) -> list[Dependency]:
    """Extract PEP 735 dependency groups."""
    groups = data.get("dependency-groups", {})
    if not groups:
        return []

    deps: list[Dependency] = []
    src = "pyproject.toml [dependency-groups]"

    for group_name, specs in groups.items():
        for spec in specs:
            if isinstance(spec, str):
                dep = _parse_pep508(spec, group=group_name, source=src)
                if dep:
                    deps.append(dep)
            # include-group entries are dicts — skip them

    return deps


def _group_from_requirements_filename(stem: str) -> str:
    """Derive a group name from a requirements file stem."""
    stem_lower = stem.lower()
    if stem_lower in ("requirements", "requirements-prod", "requirements-main"):
        return "main"
    # requirements-dev -> dev, requirements-test -> test, etc.
    for prefix in ("requirements-", "requirements_"):
        if stem_lower.startswith(prefix):
            return stem_lower[len(prefix) :]
    return "main"


def _extract_requirements_file(path: Path, *, group: str = "main") -> list[Dependency]:
    src = path.name
    deps: list[Dependency] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        dep = _parse_pep508(line, group=group, source=src)
        if dep:
            deps.append(dep)
    return deps


def _extract_pipfile(path: Path) -> list[Dependency]:
    """Best-effort Pipfile parsing (INI-like, not full TOML)."""
    deps: list[Dependency] = []
    current_group = ""
    src = "Pipfile"

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].lower()
            match section:
                case "packages":
                    current_group = "main"
                case "dev-packages":
                    current_group = "dev"
                case _:
                    current_group = ""
            continue

        if not current_group or "=" not in stripped:
            continue

        name, _, value = stripped.partition("=")
        name = name.strip().strip('"').strip("'")
        value = value.strip().strip('"').strip("'")
        version = value if value != "*" else "*"
        deps.append(Dependency(name=name, version=version, group=current_group, source=src))

    return deps
