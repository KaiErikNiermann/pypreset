"""Tests for README.md.j2 template rendering."""

from __future__ import annotations

from pypreset.models import (
    Dependencies,
    EntryPoint,
    Metadata,
    ProjectConfig,
    TypeChecker,
)
from pypreset.template_engine import (
    create_jinja_environment,
    get_template_context,
    render_template,
)


def _render_readme(
    *,
    name: str = "my-project",
    description: str = "A test project",
    license: str | None = "MIT",
    repository_url: str | None = None,
    python_version: str = "3.11",
    package_manager: str = "poetry",
    type_checker: str = "pyright",
    typing_level: str = "strict",
    testing_enabled: bool = True,
    coverage_enabled: bool = False,
    formatting_enabled: bool = True,
    formatting_tool: str = "ruff",
    pre_commit: bool = False,
    docker_enabled: bool = False,
    docker_devcontainer: bool = False,
    documentation_enabled: bool = False,
    documentation_tool: str = "none",
    deploy_gh_pages: bool = False,
    tox_enabled: bool = False,
    dependabot_enabled: bool = True,
    entry_points: list[EntryPoint] | None = None,
    layout: str = "src",
) -> str:
    """Helper to render the README template with specific settings."""
    from pypreset.models import (
        ContainerRuntime,
        CreationPackageManager,
        DependabotConfig,
        DockerConfig,
        DocumentationConfig,
        DocumentationTool,
        FormattingConfig,
        FormattingTool,
        LayoutStyle,
        TestingConfig,
        TestingFramework,
        ToxConfig,
        TypingLevel,
    )

    config = ProjectConfig(
        metadata=Metadata(
            name=name,
            description=description,
            license=license,
            repository_url=repository_url,
            python_version=python_version,
        ),
        dependencies=Dependencies(),
        testing=TestingConfig(
            enabled=testing_enabled,
            framework=TestingFramework.PYTEST,
            coverage=coverage_enabled,
        ),
        formatting=FormattingConfig(
            enabled=formatting_enabled,
            tool=FormattingTool(formatting_tool),
            pre_commit=pre_commit,
            type_checker=TypeChecker(type_checker),
        ),
        dependabot=DependabotConfig(enabled=dependabot_enabled),
        docker=DockerConfig(
            enabled=docker_enabled,
            devcontainer=docker_devcontainer,
            container_runtime=ContainerRuntime.DOCKER,
        ),
        documentation=DocumentationConfig(
            enabled=documentation_enabled,
            tool=DocumentationTool(documentation_tool),
            deploy_gh_pages=deploy_gh_pages,
        ),
        tox=ToxConfig(enabled=tox_enabled),
        typing_level=TypingLevel(typing_level),
        layout=LayoutStyle(layout),
        package_manager=CreationPackageManager(package_manager),
        entry_points=entry_points or [],
    )
    env = create_jinja_environment()
    context = get_template_context(config)
    return render_template(env, "README.md.j2", context)


class TestReadmeBadges:
    """Tests for badge rendering in README."""

    def test_no_badges_without_repo_or_license(self) -> None:
        readme = _render_readme(repository_url=None, license=None)
        assert "img.shields.io" not in readme
        assert "[![" not in readme

    def test_ci_badge_with_github_repo(self) -> None:
        readme = _render_readme(repository_url="https://github.com/user/my-project")
        assert "[![CI]" in readme
        assert "github.com/user/my-project/actions/workflows/ci.yaml/badge.svg" in readme

    def test_pypi_badge_with_github_repo(self) -> None:
        readme = _render_readme(repository_url="https://github.com/user/my-project")
        assert "[![PyPI version]" in readme
        assert "pypi.org/project/my-project" in readme

    def test_python_version_badge_with_github_repo(self) -> None:
        readme = _render_readme(
            repository_url="https://github.com/user/my-project", python_version="3.12"
        )
        assert "required-version-toml" in readme

    def test_license_badge(self) -> None:
        readme = _render_readme(license="MIT")
        assert "[![License: MIT]" in readme
        assert "license-MIT-blue" in readme

    def test_apache_license_badge_escapes_hyphen(self) -> None:
        readme = _render_readme(license="Apache-2.0")
        assert "license-Apache--2.0-blue" in readme

    def test_no_license_badge_when_none(self) -> None:
        readme = _render_readme(license=None, repository_url=None)
        assert "License:" not in readme

    def test_codecov_badge_when_coverage_enabled(self) -> None:
        readme = _render_readme(
            repository_url="https://github.com/user/my-project",
            coverage_enabled=True,
        )
        assert "[![codecov]" in readme
        assert "codecov.io/gh/user/my-project" in readme

    def test_no_codecov_badge_without_coverage(self) -> None:
        readme = _render_readme(
            repository_url="https://github.com/user/my-project",
            coverage_enabled=False,
        )
        assert "codecov" not in readme

    def test_no_badges_for_non_github_repo(self) -> None:
        readme = _render_readme(repository_url="https://gitlab.com/user/my-project", license=None)
        assert "[![CI]" not in readme
        assert "[![PyPI" not in readme


class TestReadmeInstallation:
    """Tests for installation section rendering."""

    def test_poetry_install(self) -> None:
        readme = _render_readme(package_manager="poetry")
        assert "pip install my-project" in readme
        assert "poetry install" in readme

    def test_uv_install(self) -> None:
        readme = _render_readme(package_manager="uv")
        assert "uv add my-project" in readme
        assert "uv sync" in readme

    def test_clone_url_uses_repo_when_available(self) -> None:
        readme = _render_readme(repository_url="https://github.com/user/my-project")
        assert "git clone https://github.com/user/my-project" in readme

    def test_clone_url_placeholder_when_no_repo(self) -> None:
        readme = _render_readme(repository_url=None)
        assert "YOUR_USERNAME" in readme


class TestReadmeFeatures:
    """Tests for features section rendering."""

    def test_features_section_with_testing(self) -> None:
        readme = _render_readme(testing_enabled=True)
        assert "## Features" in readme
        assert "**Pytest** test suite" in readme

    def test_features_with_coverage(self) -> None:
        readme = _render_readme(testing_enabled=True, coverage_enabled=True)
        assert "with coverage" in readme

    def test_features_with_formatting(self) -> None:
        readme = _render_readme(formatting_enabled=True, formatting_tool="ruff")
        assert "**Ruff** linting & formatting" in readme

    def test_features_with_type_checking(self) -> None:
        readme = _render_readme(typing_level="strict", type_checker="pyright")
        assert "**Pyright** type checking (strict mode)" in readme

    def test_features_with_docker(self) -> None:
        readme = _render_readme(docker_enabled=True)
        assert "**Docker** containerization" in readme

    def test_features_with_docker_devcontainer(self) -> None:
        readme = _render_readme(docker_enabled=True, docker_devcontainer=True)
        assert "with devcontainer" in readme

    def test_features_with_documentation(self) -> None:
        readme = _render_readme(
            documentation_enabled=True, documentation_tool="sphinx", deploy_gh_pages=True
        )
        assert "**Sphinx** documentation" in readme
        assert "GitHub Pages" in readme

    def test_features_with_tox(self) -> None:
        readme = _render_readme(tox_enabled=True)
        assert "**Tox** multi-environment testing" in readme

    def test_features_with_dependabot(self) -> None:
        readme = _render_readme(dependabot_enabled=True)
        assert "**Dependabot** dependency updates" in readme

    def test_features_with_pre_commit(self) -> None:
        readme = _render_readme(pre_commit=True)
        assert "**Pre-commit** hooks" in readme

    def test_no_features_section_when_nothing_enabled(self) -> None:
        readme = _render_readme(
            testing_enabled=False,
            formatting_enabled=False,
            typing_level="none",
            docker_enabled=False,
            documentation_enabled=False,
            tox_enabled=False,
            dependabot_enabled=False,
            pre_commit=False,
        )
        assert "## Features" not in readme


class TestReadmeDevelopment:
    """Tests for development section rendering."""

    def test_poetry_dev_commands(self) -> None:
        readme = _render_readme(package_manager="poetry")
        assert "poetry install" in readme
        assert "poetry run pytest" in readme
        assert "poetry run ruff check" in readme

    def test_uv_dev_commands(self) -> None:
        readme = _render_readme(package_manager="uv")
        assert "uv sync" in readme
        assert "uv run pytest" in readme
        assert "uv run ruff check" in readme

    def test_pyright_type_check_command(self) -> None:
        readme = _render_readme(type_checker="pyright", typing_level="strict")
        assert "pyright src/" in readme
        assert "mypy" not in readme

    def test_ty_type_check_command(self) -> None:
        readme = _render_readme(type_checker="ty", typing_level="strict")
        assert "ty check src/" in readme

    def test_mypy_type_check_command(self) -> None:
        readme = _render_readme(type_checker="mypy", typing_level="strict")
        assert "mypy src/" in readme

    def test_no_type_check_when_none(self) -> None:
        readme = _render_readme(typing_level="none")
        assert "Type check" not in readme

    def test_coverage_command_when_enabled(self) -> None:
        readme = _render_readme(testing_enabled=True, coverage_enabled=True)
        assert "pytest --cov" in readme

    def test_black_formatting_command(self) -> None:
        readme = _render_readme(formatting_tool="black")
        assert "black ." in readme


class TestReadmeStructure:
    """Tests for project structure and other sections."""

    def test_project_structure_shown_for_cli(self) -> None:
        readme = _render_readme(entry_points=[EntryPoint(name="mycli", module="pkg.cli:app")])
        assert "## Project Structure" in readme
        assert "cli.py" in readme

    def test_no_project_structure_for_library(self) -> None:
        readme = _render_readme(entry_points=[])
        assert "## Project Structure" not in readme

    def test_src_layout_structure(self) -> None:
        readme = _render_readme(
            entry_points=[EntryPoint(name="mycli", module="pkg.cli:app")],
            layout="src",
        )
        assert "src/" in readme

    def test_flat_layout_structure(self) -> None:
        readme = _render_readme(
            name="my-project",
            entry_points=[EntryPoint(name="mycli", module="pkg.cli:app")],
            layout="flat",
        )
        # Should show package dir directly, not under src/
        content = readme.split("## Project Structure")[1].split("##")[0]
        assert "src/" not in content
        assert "my_project/" in content

    def test_contributing_section(self) -> None:
        readme = _render_readme()
        assert "## Contributing" in readme
        assert "Pull Request" in readme

    def test_license_section_with_license(self) -> None:
        readme = _render_readme(license="MIT")
        assert "## License" in readme
        assert "MIT License" in readme

    def test_license_section_with_repo_link(self) -> None:
        readme = _render_readme(license="MIT", repository_url="https://github.com/user/my-project")
        assert "[LICENSE]" in readme

    def test_license_section_without_license(self) -> None:
        readme = _render_readme(license=None)
        assert "## License" in readme
        assert "[LICENSE](LICENSE)" in readme

    def test_title_is_project_name(self) -> None:
        readme = _render_readme(name="cool-project")
        assert readme.startswith("# cool-project")

    def test_description_present(self) -> None:
        readme = _render_readme(description="A very cool project")
        assert "A very cool project" in readme
