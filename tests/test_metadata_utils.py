"""Tests for metadata_utils module."""

from pathlib import Path

import tomli_w

from pypreset.metadata_utils import (
    check_publish_readiness,
    generate_default_urls,
    read_pyproject_metadata,
    set_pyproject_metadata,
)


def _write_toml(path: Path, data: dict) -> None:
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


class TestReadPoetryMetadata:
    def test_reads_basic_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {
                "tool": {
                    "poetry": {
                        "name": "my-pkg",
                        "version": "1.0.0",
                        "description": "A test package",
                        "authors": ["Alice <alice@example.com>"],
                    }
                }
            },
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["name"] == "my-pkg"
        assert meta["version"] == "1.0.0"
        assert meta["description"] == "A test package"
        assert meta["authors"] == ["Alice <alice@example.com>"]

    def test_reads_url_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {
                "tool": {
                    "poetry": {
                        "name": "my-pkg",
                        "urls": {
                            "Repository": "https://github.com/user/my-pkg",
                            "Homepage": "https://my-pkg.dev",
                            "Bug Tracker": "https://github.com/user/my-pkg/issues",
                        },
                    }
                }
            },
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["repository_url"] == "https://github.com/user/my-pkg"
        assert meta["homepage_url"] == "https://my-pkg.dev"
        assert meta["bug_tracker_url"] == "https://github.com/user/my-pkg/issues"
        assert meta["documentation_url"] is None

    def test_missing_urls_are_none(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "test"}}},
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["repository_url"] is None
        assert meta["homepage_url"] is None


class TestReadPep621Metadata:
    def test_reads_basic_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {
                "project": {
                    "name": "my-pkg",
                    "version": "2.0.0",
                    "description": "PEP 621 package",
                    "authors": [{"name": "Bob", "email": "bob@example.com"}],
                }
            },
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["name"] == "my-pkg"
        assert meta["version"] == "2.0.0"
        assert meta["authors"] == ["Bob <bob@example.com>"]

    def test_reads_url_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {
                "project": {
                    "name": "my-pkg",
                    "urls": {
                        "Repository": "https://github.com/org/my-pkg",
                        "Documentation": "https://docs.my-pkg.dev",
                    },
                }
            },
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["repository_url"] == "https://github.com/org/my-pkg"
        assert meta["documentation_url"] == "https://docs.my-pkg.dev"

    def test_reads_keywords(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"project": {"name": "my-pkg", "keywords": ["python", "cli"]}},
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["keywords"] == ["python", "cli"]


class TestSetPoetryMetadata:
    def test_sets_empty_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "my-pkg", "description": ""}}},
        )
        set_pyproject_metadata(tmp_path, {"description": "Updated desc", "license": "MIT"})
        meta = read_pyproject_metadata(tmp_path)
        assert meta["description"] == "Updated desc"
        assert meta["license"] == "MIT"

    def test_skips_nonempty_without_overwrite(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "my-pkg", "description": "Original"}}},
        )
        set_pyproject_metadata(tmp_path, {"description": "Replaced"})
        meta = read_pyproject_metadata(tmp_path)
        assert meta["description"] == "Original"

    def test_overwrites_with_flag(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "my-pkg", "description": "Original"}}},
        )
        set_pyproject_metadata(tmp_path, {"description": "Replaced"}, overwrite=True)
        meta = read_pyproject_metadata(tmp_path)
        assert meta["description"] == "Replaced"

    def test_sets_url_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "my-pkg"}}},
        )
        set_pyproject_metadata(
            tmp_path,
            {
                "repository_url": "https://github.com/user/my-pkg",
                "bug_tracker_url": "https://github.com/user/my-pkg/issues",
            },
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["repository_url"] == "https://github.com/user/my-pkg"
        assert meta["bug_tracker_url"] == "https://github.com/user/my-pkg/issues"

    def test_returns_warnings(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"tool": {"poetry": {"name": "my-pkg", "description": ""}}},
        )
        warnings = set_pyproject_metadata(tmp_path, {"license": "MIT"})
        assert any("description" in w for w in warnings)


class TestSetPep621Metadata:
    def test_sets_basic_fields(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"project": {"name": "my-pkg"}},
        )
        set_pyproject_metadata(
            tmp_path,
            {"description": "A cool package", "keywords": ["cool", "package"]},
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["description"] == "A cool package"
        assert meta["keywords"] == ["cool", "package"]

    def test_sets_authors_pep621_format(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"project": {"name": "my-pkg"}},
        )
        set_pyproject_metadata(
            tmp_path,
            {"authors": ["Alice <alice@test.com>"]},
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["authors"] == ["Alice <alice@test.com>"]

    def test_sets_urls(self, tmp_path: Path) -> None:
        _write_toml(
            tmp_path / "pyproject.toml",
            {"project": {"name": "my-pkg"}},
        )
        set_pyproject_metadata(
            tmp_path,
            {"repository_url": "https://github.com/org/my-pkg"},
        )
        meta = read_pyproject_metadata(tmp_path)
        assert meta["repository_url"] == "https://github.com/org/my-pkg"


class TestCheckPublishReadiness:
    def test_empty_metadata_has_warnings(self) -> None:
        data = {"tool": {"poetry": {"name": "test", "description": ""}}}
        warnings = check_publish_readiness(data)
        assert len(warnings) >= 3
        field_names = " ".join(warnings)
        assert "description" in field_names
        assert "authors" in field_names
        assert "license" in field_names

    def test_complete_metadata_no_warnings(self) -> None:
        data = {
            "tool": {
                "poetry": {
                    "name": "test",
                    "description": "A real description",
                    "authors": ["Dev <dev@example.com>"],
                    "license": "MIT",
                    "keywords": ["python"],
                    "urls": {"Repository": "https://github.com/user/test"},
                }
            }
        }
        warnings = check_publish_readiness(data)
        assert warnings == []

    def test_default_description_warns(self) -> None:
        data = {
            "tool": {
                "poetry": {
                    "name": "test",
                    "description": "A Python package",
                    "authors": ["Dev <dev@test.com>"],
                    "license": "MIT",
                    "keywords": ["python"],
                    "urls": {"Repository": "https://github.com/user/test"},
                }
            }
        }
        warnings = check_publish_readiness(data)
        assert any("default" in w for w in warnings)

    def test_placeholder_author_warns(self) -> None:
        data = {
            "tool": {
                "poetry": {
                    "name": "test",
                    "description": "Desc",
                    "authors": ["Your Name <you@example.com>"],
                }
            }
        }
        warnings = check_publish_readiness(data)
        assert any("placeholder" in w for w in warnings)


class TestGenerateDefaultUrls:
    def test_generates_github_urls(self) -> None:
        urls = generate_default_urls("my-pkg", github_owner="myuser")
        assert urls["repository_url"] == "https://github.com/myuser/my-pkg"
        assert urls["homepage_url"] == "https://github.com/myuser/my-pkg"
        assert urls["bug_tracker_url"] == "https://github.com/myuser/my-pkg/issues"

    def test_no_owner_returns_empty(self) -> None:
        urls = generate_default_urls("my-pkg")
        assert urls == {}

    def test_org_owner(self) -> None:
        urls = generate_default_urls("tool", github_owner="my-org")
        assert "my-org" in urls["repository_url"]


class TestReadErrors:
    def test_no_pyproject_raises(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(FileNotFoundError):
            read_pyproject_metadata(tmp_path)

    def test_no_project_section_raises(self, tmp_path: Path) -> None:
        import pytest

        _write_toml(tmp_path / "pyproject.toml", {"build-system": {}})
        with pytest.raises(ValueError, match="neither"):
            read_pyproject_metadata(tmp_path)
