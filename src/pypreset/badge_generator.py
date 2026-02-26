"""Badge link generation for Python project READMEs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Badge:
    """A single badge with label and markdown text."""

    label: str
    markdown: str


def _extract_gh_owner_repo(repository_url: str | None) -> str | None:
    """Extract 'owner/repo' from a GitHub URL."""
    if not repository_url or "github.com/" not in repository_url:
        return None
    return repository_url.rstrip("/").split("github.com/")[1]


def generate_badges(
    project_name: str,
    *,
    repository_url: str | None = None,
    license_id: str | None = None,
    has_coverage: bool = False,
    python_version: str | None = None,
) -> list[Badge]:
    """Generate badge markdown links for a Python project.

    Args:
        project_name: The PyPI package name.
        repository_url: GitHub repository URL (enables CI, Python version, Codecov badges).
        license_id: SPDX license identifier (e.g. "MIT").
        has_coverage: Whether coverage is configured (enables Codecov badge).
        python_version: Minimum Python version for display purposes.

    Returns:
        List of Badge instances with label and markdown text.
    """
    badges: list[Badge] = []
    gh = _extract_gh_owner_repo(repository_url)

    if gh:
        badges.append(
            Badge(
                "CI",
                f"[![CI](https://github.com/{gh}/actions/workflows/ci.yaml/badge.svg)]"
                f"(https://github.com/{gh}/actions/workflows/ci.yaml)",
            )
        )

        badges.append(
            Badge(
                "PyPI",
                f"[![PyPI version](https://img.shields.io/pypi/v/{project_name})]"
                f"(https://pypi.org/project/{project_name}/)",
            )
        )

        gh_encoded = gh.replace("/", "%2F")
        badges.append(
            Badge(
                "Python",
                f"[![Python {python_version or '3'}+]"
                f"(https://img.shields.io/python/required-version-toml"
                f"?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2F"
                f"{gh_encoded}%2Fmain%2Fpyproject.toml)]"
                f"(https://pypi.org/project/{project_name}/)",
            )
        )

    if license_id:
        escaped = license_id.replace("-", "--")
        badges.append(
            Badge(
                "License",
                f"[![License: {license_id}]"
                f"(https://img.shields.io/badge/license-{escaped}-blue.svg)]"
                f"(https://opensource.org/licenses/{license_id})",
            )
        )

    if has_coverage and gh:
        badges.append(
            Badge(
                "Codecov",
                f"[![codecov](https://codecov.io/gh/{gh}/graph/badge.svg)]"
                f"(https://codecov.io/gh/{gh})",
            )
        )

    return badges
