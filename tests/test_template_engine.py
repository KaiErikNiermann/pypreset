"""Tests for template engine functionality."""

from pypreset.models import (
    Dependencies,
    EntryPoint,
    Metadata,
    ProjectConfig,
)
from pypreset.template_engine import (
    create_jinja_environment,
    get_template_context,
    get_templates_dir,
    render_content,
    render_path,
    render_template,
)


class TestGetTemplatesDir:
    """Tests for get_templates_dir function."""

    def test_templates_dir_exists(self) -> None:
        """Test that templates directory exists."""
        templates_dir = get_templates_dir()
        assert templates_dir.exists()
        assert templates_dir.is_dir()


class TestCreateJinjaEnvironment:
    """Tests for create_jinja_environment function."""

    def test_environment_can_load_templates(self) -> None:
        """Test that environment can load built-in templates."""
        env = create_jinja_environment()

        # Should be able to get template list
        templates = env.list_templates()
        assert len(templates) > 0
        assert "pyproject.toml.j2" in templates


class TestGetTemplateContext:
    """Tests for get_template_context function."""

    def test_basic_context(self) -> None:
        """Test context generation for basic config."""
        config = ProjectConfig(
            metadata=Metadata(
                name="test-project",
                version="1.0.0",
                description="A test project",
            ),
        )

        context = get_template_context(config)

        assert context["project"]["name"] == "test-project"
        assert context["project"]["package_name"] == "test_project"
        assert context["project"]["version"] == "1.0.0"

    def test_hyphenated_name_conversion(self) -> None:
        """Test that hyphenated names are converted to underscores."""
        config = ProjectConfig(
            metadata=Metadata(name="my-cool-project"),
        )

        context = get_template_context(config)

        assert context["project"]["name"] == "my-cool-project"
        assert context["project"]["package_name"] == "my_cool_project"

    def test_dependencies_in_context(self) -> None:
        """Test that dependencies are included in context."""
        config = ProjectConfig(
            metadata=Metadata(name="test"),
            dependencies=Dependencies(
                main=["requests", "pandas"],
                dev=["pytest"],
            ),
        )

        context = get_template_context(config)

        assert "requests" in context["dependencies"]["main"]
        assert "pytest" in context["dependencies"]["dev"]

    def test_entry_points_in_context(self) -> None:
        """Test that entry points are included in context."""
        config = ProjectConfig(
            metadata=Metadata(name="test-cli"),
            entry_points=[
                EntryPoint(name="test-cli", module="test_cli.cli:app"),
            ],
        )

        context = get_template_context(config)

        assert len(context["entry_points"]) == 1
        assert context["entry_points"][0]["name"] == "test-cli"
        assert context["entry_points"][0]["module"] == "test_cli.cli:app"


class TestRenderContent:
    """Tests for render_content function."""

    def test_simple_variable_substitution(self) -> None:
        """Test simple variable substitution."""
        content = "Hello, {{ name }}!"
        result = render_content(content, {"name": "World"})
        assert result == "Hello, World!"

    def test_nested_variable(self) -> None:
        """Test nested variable substitution."""
        content = "Project: {{ project.name }}"
        result = render_content(content, {"project": {"name": "test"}})
        assert result == "Project: test"

    def test_conditionals(self) -> None:
        """Test conditional rendering."""
        content = "{% if enabled %}Enabled{% else %}Disabled{% endif %}"

        assert render_content(content, {"enabled": True}) == "Enabled"
        assert render_content(content, {"enabled": False}) == "Disabled"


class TestRenderPath:
    """Tests for render_path function."""

    def test_simple_path(self) -> None:
        """Test rendering a simple path."""
        path = "src/{{ project.package_name }}/__init__.py"
        result = render_path(path, {"project": {"package_name": "my_project"}})
        assert result == "src/my_project/__init__.py"

    def test_path_without_variables(self) -> None:
        """Test rendering a path without variables."""
        path = "README.md"
        result = render_path(path, {})
        assert result == "README.md"


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_render_pyproject_toml(self) -> None:
        """Test rendering pyproject.toml template."""
        env = create_jinja_environment()
        context = {
            "project": {
                "name": "test-project",
                "package_name": "test_project",
                "version": "0.1.0",
                "description": "A test project",
                "authors": ["Test <test@example.com>"],
                "license": None,
                "readme": "README.md",
                "python_version": "3.11",
                "keywords": [],
                "classifiers": [],
            },
            "dependencies": {
                "main": [],
                "dev": [],
                "optional": {},
            },
            "testing": {
                "enabled": True,
                "framework": "pytest",
                "coverage": False,
                "coverage_config": {
                    "enabled": False,
                    "tool": "none",
                    "threshold": None,
                    "ignore_patterns": [],
                },
            },
            "formatting": {
                "enabled": True,
                "tool": "ruff",
                "line_length": 100,
                "radon": False,
                "pre_commit": False,
                "version_bumping": False,
                "type_checker": "mypy",
            },
            "documentation": {
                "enabled": False,
                "tool": "none",
                "deploy_gh_pages": False,
            },
            "tox": {
                "enabled": False,
            },
            "typing_level": "strict",
            "layout": "src",
            "package_manager": "poetry",
            "entry_points": [],
            "extras": {},
        }

        result = render_template(env, "pyproject.toml.j2", context)

        assert 'name = "test-project"' in result
        assert 'version = "0.1.0"' in result
        assert "[tool.poetry]" in result
        assert "[build-system]" in result

    def test_render_pyproject_with_urls(self) -> None:
        env = create_jinja_environment()
        context = {
            "project": {
                "name": "test-project",
                "package_name": "test_project",
                "version": "0.1.0",
                "description": "A test project",
                "authors": ["Test <test@example.com>"],
                "license": "MIT",
                "readme": "README.md",
                "python_version": "3.11",
                "keywords": ["python", "test"],
                "classifiers": [],
                "repository_url": "https://github.com/user/test-project",
                "homepage_url": "https://test-project.dev",
                "documentation_url": None,
                "bug_tracker_url": "https://github.com/user/test-project/issues",
            },
            "dependencies": {"main": [], "dev": [], "optional": {}},
            "testing": {
                "enabled": False,
                "framework": "pytest",
                "coverage": False,
                "coverage_config": {
                    "enabled": False,
                    "tool": "none",
                    "threshold": None,
                    "ignore_patterns": [],
                },
            },
            "formatting": {
                "enabled": False,
                "tool": "ruff",
                "line_length": 100,
                "radon": False,
                "pre_commit": False,
                "version_bumping": False,
                "type_checker": "mypy",
            },
            "documentation": {"enabled": False, "tool": "none", "deploy_gh_pages": False},
            "tox": {"enabled": False},
            "typing_level": "none",
            "layout": "src",
            "package_manager": "poetry",
            "entry_points": [],
            "extras": {},
        }

        result = render_template(env, "pyproject.toml.j2", context)
        assert "[tool.poetry.urls]" in result
        assert 'Repository = "https://github.com/user/test-project"' in result
        assert 'Homepage = "https://test-project.dev"' in result
        assert '"Bug Tracker" = "https://github.com/user/test-project/issues"' in result
        assert "Documentation" not in result
        assert 'license = "MIT"' in result
        assert 'keywords = ["python", "test"]' in result

    def test_render_pyproject_uv_with_urls(self) -> None:
        env = create_jinja_environment()
        context = {
            "project": {
                "name": "uv-project",
                "package_name": "uv_project",
                "version": "0.1.0",
                "description": "A uv project",
                "authors": ["Dev <dev@test.com>"],
                "license": "Apache-2.0",
                "readme": "README.md",
                "python_version": "3.12",
                "keywords": ["uv"],
                "classifiers": [],
                "repository_url": "https://github.com/org/uv-project",
                "homepage_url": None,
                "documentation_url": "https://uv-project.readthedocs.io",
                "bug_tracker_url": None,
            },
            "dependencies": {"main": [], "dev": [], "optional": {}},
            "testing": {
                "enabled": False,
                "framework": "pytest",
                "coverage": False,
                "coverage_config": {
                    "enabled": False,
                    "tool": "none",
                    "threshold": None,
                    "ignore_patterns": [],
                },
            },
            "formatting": {
                "enabled": False,
                "tool": "ruff",
                "line_length": 100,
                "radon": False,
                "pre_commit": False,
                "version_bumping": False,
                "type_checker": "mypy",
            },
            "documentation": {"enabled": False, "tool": "none", "deploy_gh_pages": False},
            "tox": {"enabled": False},
            "typing_level": "none",
            "layout": "src",
            "package_manager": "uv",
            "entry_points": [],
            "extras": {},
        }

        result = render_template(env, "pyproject_uv.toml.j2", context)
        assert "[project.urls]" in result
        assert 'Repository = "https://github.com/org/uv-project"' in result
        assert 'Documentation = "https://uv-project.readthedocs.io"' in result
        assert "Homepage" not in result
        assert 'keywords = ["uv"]' in result
