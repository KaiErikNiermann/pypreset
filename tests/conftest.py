"""Pytest fixtures for pysetup tests."""

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary directory for project generation."""
    output_dir = tmp_path / "projects"
    output_dir.mkdir(parents=True, exist_ok=True)
    yield output_dir


@pytest.fixture
def presets_dir() -> Path:
    """Get the built-in presets directory."""
    return Path(__file__).parent.parent / "src" / "pysetup" / "presets"
