"""Tests for the inspect module (project tree + dependency extraction)."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import pytest

from pypreset.inspect import (
    Dependency,
    _group_from_requirements_filename,
    _parse_pep508,
    extract_dependencies,
    project_tree,
)

# ── project_tree tests ────────────────────────────────────────────────────


class TestProjectTree:
    """Tests for project_tree()."""

    def test_simple_tree(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").touch()
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").touch()
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "README.md").touch()

        tree = project_tree(tmp_path)

        assert tree.startswith(tmp_path.name + "/")
        assert "src" in tree
        assert "main.py" in tree
        assert "tests" in tree
        assert "pyproject.toml" in tree
        assert "README.md" in tree

    def test_hides_pycache(self, tmp_path: Path) -> None:
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.cpython-311.pyc").touch()
        (tmp_path / "app.py").touch()

        tree = project_tree(tmp_path)

        assert "__pycache__" not in tree
        assert "app.py" in tree

    def test_hides_dotfiles(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").touch()
        (tmp_path / "visible.py").touch()

        tree = project_tree(tmp_path)

        assert ".git" not in tree
        assert ".env" not in tree
        assert "visible.py" in tree

    def test_hides_venv(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").mkdir()
        (tmp_path / "venv").mkdir()
        (tmp_path / "app.py").touch()

        tree = project_tree(tmp_path)
        # Check tree lines (skip root line which contains tmp_path name)
        tree_lines = tree.split("\n")[1:]

        assert not any("venv" in line for line in tree_lines)
        assert "app.py" in tree

    def test_hides_node_modules(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "package.json").touch()

        tree = project_tree(tmp_path)
        tree_lines = tree.split("\n")[1:]

        assert not any("node_modules" in line for line in tree_lines)
        assert "package.json" in tree

    def test_hides_egg_info(self, tmp_path: Path) -> None:
        (tmp_path / "mypackage.egg-info").mkdir()
        (tmp_path / "setup.py").touch()

        tree = project_tree(tmp_path)

        assert "egg-info" not in tree
        assert "setup.py" in tree

    def test_max_depth_limits_recursion(self, tmp_path: Path) -> None:
        d = tmp_path / "a" / "b"
        d.mkdir(parents=True)
        (d / "deep.txt").touch()

        tree_shallow = project_tree(tmp_path, max_depth=1)
        tree_deep = project_tree(tmp_path, max_depth=3)

        assert "deep.txt" not in tree_shallow
        assert "deep.txt" in tree_deep

    def test_directories_before_files(self, tmp_path: Path) -> None:
        (tmp_path / "zebra.py").touch()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "alpha" / "file.py").touch()

        tree = project_tree(tmp_path)
        lines = tree.split("\n")

        # Find positions
        alpha_line = next(i for i, line in enumerate(lines) if "alpha" in line)
        zebra_line = next(i for i, line in enumerate(lines) if "zebra" in line)
        assert alpha_line < zebra_line

    def test_not_a_directory_raises(self, tmp_path: Path) -> None:
        fake = tmp_path / "not-a-dir"
        with pytest.raises(FileNotFoundError, match="Not a directory"):
            project_tree(fake)

    def test_uses_tree_drawing_chars(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()

        tree = project_tree(tmp_path)
        # Should contain box-drawing characters
        assert "├── " in tree or "└── " in tree

    def test_empty_directory(self, tmp_path: Path) -> None:
        tree = project_tree(tmp_path)
        # Just the root line
        assert tree == tmp_path.name + "/"


# ── _parse_pep508 tests ──────────────────────────────────────────────────


class TestParsePep508:
    """Tests for PEP 508 requirement string parsing."""

    def test_name_only(self) -> None:
        dep = _parse_pep508("requests")
        assert dep is not None
        assert dep.name == "requests"
        assert dep.version == "*"

    def test_with_version(self) -> None:
        dep = _parse_pep508("requests>=2.28.0")
        assert dep is not None
        assert dep.name == "requests"
        assert dep.version == ">=2.28.0"

    def test_with_extras(self) -> None:
        dep = _parse_pep508("uvicorn[standard]>=0.20")
        assert dep is not None
        assert dep.name == "uvicorn"
        assert dep.extras == ["standard"]
        assert dep.version == ">=0.20"

    def test_with_multiple_extras(self) -> None:
        dep = _parse_pep508("package[extra1,extra2]>=1.0")
        assert dep is not None
        assert dep.extras == ["extra1", "extra2"]

    def test_with_environment_marker(self) -> None:
        dep = _parse_pep508('tomli>=1.0; python_version < "3.11"')
        assert dep is not None
        assert dep.name == "tomli"
        assert dep.version == ">=1.0"

    def test_empty_string(self) -> None:
        assert _parse_pep508("") is None

    def test_comment_line(self) -> None:
        assert _parse_pep508("# a comment") is None

    def test_group_and_source(self) -> None:
        dep = _parse_pep508("pytest>=7.0", group="dev", source="requirements-dev.txt")
        assert dep is not None
        assert dep.group == "dev"
        assert dep.source == "requirements-dev.txt"

    def test_complex_version(self) -> None:
        dep = _parse_pep508("numpy>=1.24,<2.0")
        assert dep is not None
        assert dep.name == "numpy"
        assert dep.version == ">=1.24,<2.0"


# ── _group_from_requirements_filename tests ──────────────────────────────


class TestGroupFromFilename:
    """Tests for requirements filename → group mapping."""

    def test_requirements(self) -> None:
        assert _group_from_requirements_filename("requirements") == "main"

    def test_requirements_dev(self) -> None:
        assert _group_from_requirements_filename("requirements-dev") == "dev"

    def test_requirements_test(self) -> None:
        assert _group_from_requirements_filename("requirements-test") == "test"

    def test_requirements_underscore(self) -> None:
        assert _group_from_requirements_filename("requirements_dev") == "dev"

    def test_requirements_prod(self) -> None:
        assert _group_from_requirements_filename("requirements-prod") == "main"


# ── extract_dependencies tests ───────────────────────────────────────────


class TestExtractDependencies:
    """Tests for extract_dependencies()."""

    def test_poetry_deps(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.28"
click = {version = "^8.0", extras = ["testing"]}

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
ruff = "^0.1.0"
"""
        )

        deps = extract_dependencies(tmp_path)
        names = {d.name for d in deps}

        assert "requests" in names
        assert "click" in names
        assert "pytest" in names
        assert "ruff" in names
        assert "python" not in names  # filtered out

        requests_dep = next(d for d in deps if d.name == "requests")
        assert requests_dep.version == "^2.28"
        assert requests_dep.group == "main"

        click_dep = next(d for d in deps if d.name == "click")
        assert click_dep.extras == ["testing"]

        pytest_dep = next(d for d in deps if d.name == "pytest")
        assert pytest_dep.group == "dev"

    def test_poetry_old_style_dev(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
"""
        )

        deps = extract_dependencies(tmp_path)
        pytest_dep = next(d for d in deps if d.name == "pytest")
        assert pytest_dep.group == "dev"

    def test_pep621_deps(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[project]
dependencies = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
]
test = [
    "httpx>=0.24",
]
"""
        )

        deps = extract_dependencies(tmp_path)
        names = {d.name for d in deps}

        assert "fastapi" in names
        assert "uvicorn" in names
        assert "pytest" in names
        assert "httpx" in names

        fastapi = next(d for d in deps if d.name == "fastapi")
        assert fastapi.group == "main"
        assert fastapi.version == ">=0.100"

        httpx = next(d for d in deps if d.name == "httpx")
        assert httpx.group == "test"

    def test_dependency_groups_pep735(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[dependency-groups]
test = ["pytest>=8.0", "coverage>=7.0"]
"""
        )

        deps = extract_dependencies(tmp_path)
        names = {d.name for d in deps}

        assert "pytest" in names
        assert "coverage" in names

        pytest_dep = next(d for d in deps if d.name == "pytest")
        assert pytest_dep.group == "test"

    def test_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text(
            """
requests>=2.28
flask==2.3.0
# A comment
-e ./local-package
"""
        )

        deps = extract_dependencies(tmp_path)
        names = {d.name for d in deps}

        assert "requests" in names
        assert "flask" in names
        assert len(deps) == 2  # comment and -e lines skipped

        flask = next(d for d in deps if d.name == "flask")
        assert flask.version == "==2.3.0"
        assert flask.group == "main"

    def test_requirements_dev_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements-dev.txt").write_text("pytest>=7.0\n")

        deps = extract_dependencies(tmp_path)
        assert len(deps) == 1
        assert deps[0].group == "dev"

    def test_pipfile(self, tmp_path: Path) -> None:
        (tmp_path / "Pipfile").write_text(
            """
[packages]
requests = ">=2.28"
flask = "*"

[dev-packages]
pytest = ">=7.0"
"""
        )

        deps = extract_dependencies(tmp_path)
        names = {d.name for d in deps}

        assert "requests" in names
        assert "flask" in names
        assert "pytest" in names

        flask = next(d for d in deps if d.name == "flask")
        assert flask.version == "*"
        assert flask.group == "main"

        pytest_dep = next(d for d in deps if d.name == "pytest")
        assert pytest_dep.group == "dev"

    def test_no_deps_found(self, tmp_path: Path) -> None:
        deps = extract_dependencies(tmp_path)
        assert deps == []

    def test_deduplication(self, tmp_path: Path) -> None:
        """If same dep appears in both Poetry and PEP 621 sections, keep first."""
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.28"

[project]
dependencies = ["requests>=2.28"]
"""
        )

        deps = extract_dependencies(tmp_path)
        request_deps = [d for d in deps if d.name == "requests"]
        assert len(request_deps) == 1

    def test_sorted_by_group_then_name(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.11"
zebra = "^1.0"
alpha = "^2.0"

[tool.poetry.group.dev.dependencies]
beta = "^3.0"
"""
        )

        deps = extract_dependencies(tmp_path)
        groups = [d.group for d in deps]
        # dev comes before main alphabetically
        assert groups == ["dev", "main", "main"]
        main_deps = [d for d in deps if d.group == "main"]
        assert main_deps[0].name == "alpha"
        assert main_deps[1].name == "zebra"


class TestDependencyToDict:
    """Tests for Dependency.to_dict()."""

    def test_basic(self) -> None:
        dep = Dependency(name="requests", version=">=2.28", group="main")
        d = dep.to_dict()
        assert d == {"name": "requests", "version": ">=2.28", "group": "main"}

    def test_with_extras(self) -> None:
        dep = Dependency(name="uvicorn", version=">=0.20", extras=["standard"], group="main")
        d = dep.to_dict()
        assert d["extras"] == ["standard"]

    def test_with_source(self) -> None:
        dep = Dependency(
            name="pytest",
            version=">=7.0",
            group="dev",
            source="requirements-dev.txt",
        )
        d = dep.to_dict()
        assert d["source"] == "requirements-dev.txt"

    def test_no_extras_or_source_omitted(self) -> None:
        dep = Dependency(name="click", version="^8.0", group="main")
        d = dep.to_dict()
        assert "extras" not in d
        assert "source" not in d
