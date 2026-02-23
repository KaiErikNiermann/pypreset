"""Tests for docker_utils module."""

from pypreset.docker_utils import resolve_docker_base_image


class TestResolveDockerBaseImage:
    """Tests for resolve_docker_base_image."""

    def test_derives_from_python_version(self) -> None:
        """Test that base image is derived from python version."""
        result = resolve_docker_base_image("3.11")
        assert result == "python:3.11-slim"

    def test_derives_from_different_version(self) -> None:
        """Test derivation with a different python version."""
        result = resolve_docker_base_image("3.13")
        assert result == "python:3.13-slim"

    def test_explicit_override(self) -> None:
        """Test that explicit base_image is returned as-is."""
        result = resolve_docker_base_image("3.11", base_image="ubuntu:22.04")
        assert result == "ubuntu:22.04"

    def test_none_override_derives_from_version(self) -> None:
        """Test that None base_image falls back to version-based derivation."""
        result = resolve_docker_base_image("3.12", base_image=None)
        assert result == "python:3.12-slim"
