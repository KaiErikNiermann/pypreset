"""Project generator - creates projects from configurations."""

import logging
import stat
import subprocess
from pathlib import Path

from pypreset.models import (
    CreationPackageManager,
    FileTemplate,
    LayoutStyle,
    ProjectConfig,
)
from pypreset.template_engine import (
    create_jinja_environment,
    get_template_context,
    render_content,
    render_path,
    render_template,
)

logger = logging.getLogger(__name__)


class ProjectGenerator:
    """Generates a project from a configuration."""

    def __init__(self, config: ProjectConfig, output_dir: Path) -> None:
        self.config = config
        self.output_dir = output_dir
        self.project_dir = output_dir / config.metadata.name
        self.env = create_jinja_environment()
        self.context = get_template_context(config)
        self._is_src = config.layout == LayoutStyle.SRC
        self._is_uv = config.package_manager == CreationPackageManager.UV
        self._is_podman = config.docker.container_runtime.value == "podman"

    @property
    def _package_dir(self) -> Path:
        """Return the package directory based on layout style."""
        package_name = self.context["project"]["package_name"]
        if self._is_src:
            return self.project_dir / "src" / package_name
        return self.project_dir / package_name

    def generate(self) -> Path:
        """Generate the complete project structure."""
        logger.info(f"Generating project '{self.config.metadata.name}' at {self.project_dir}")

        # Create project directory
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        self._create_directories()

        # Create files from templates
        self._create_files()

        # Create pyproject.toml
        self._create_pyproject_toml()

        # Create README.md
        self._create_readme()

        # Create additional standard files
        self._create_gitignore()

        # Create GitHub workflows
        self._create_github_workflows()

        # Create pre-commit config if enabled
        if self.config.formatting.pre_commit:
            self._create_pre_commit_config()

        # Create Docker files if enabled
        if self.config.docker.enabled:
            self._create_docker_files()

        # Create devcontainer if enabled
        if self.config.docker.devcontainer:
            self._create_devcontainer()

        # Create codecov config if enabled
        if (
            self.config.testing.coverage_config.enabled
            and self.config.testing.coverage_config.tool.value == "codecov"
        ):
            self._create_codecov_config()

        # Create documentation scaffolding if enabled
        if self.config.documentation.enabled:
            self._create_documentation()

        # Create tox config if enabled
        if self.config.tox.enabled:
            self._create_tox_config()

        logger.info(f"Project '{self.config.metadata.name}' generated successfully")
        return self.project_dir

    def _create_directories(self) -> None:
        """Create all directories in the project structure."""
        # Create the package directory (src-layout: src/pkg, flat-layout: pkg/)
        self._package_dir.mkdir(parents=True, exist_ok=True)

        # Create directories from structure config
        for dir_path in self.config.structure.directories:
            rendered_path = render_path(dir_path, self.context)
            full_path = self.project_dir / rendered_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {full_path}")

        # Create tests directory if testing is enabled
        if self.config.testing.enabled:
            tests_dir = self.project_dir / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)

    def _create_files(self) -> None:
        """Create all files from templates or inline content."""
        for file_def in self.config.structure.files:
            self._create_file(file_def)

        # Always create __init__.py for the package
        init_path = self._package_dir / "__init__.py"
        if not init_path.exists():
            name = self.config.metadata.name
            version = self.config.metadata.version
            init_content = f'"""{name} package."""\n\n__version__ = "{version}"\n'
            init_path.write_text(init_content)

        # Create tests/__init__.py and test file if testing is enabled
        if self.config.testing.enabled:
            tests_init = self.project_dir / "tests" / "__init__.py"
            if not tests_init.exists():
                tests_init.write_text('"""Tests package."""\n')

            test_file = self.project_dir / "tests" / "test_basic.py"
            if not test_file.exists():
                test_content = self._render_test_file()
                test_file.write_text(test_content)

    def _create_file(self, file_def: FileTemplate) -> None:
        """Create a single file from a template or inline content."""
        rendered_path = render_path(file_def.path, self.context)
        full_path = self.project_dir / rendered_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Get content from template or inline
        if file_def.template:
            content = render_template(self.env, file_def.template, self.context)
        elif file_def.content:
            content = render_content(file_def.content, self.context)
        else:
            content = ""

        full_path.write_text(content)
        logger.debug(f"Created file: {full_path}")

        # Make executable if needed
        if file_def.executable:
            current_mode = full_path.stat().st_mode
            full_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _create_pyproject_toml(self) -> None:
        """Create the pyproject.toml file."""
        template = "pyproject_uv.toml.j2" if self._is_uv else "pyproject.toml.j2"
        content = render_template(self.env, template, self.context)
        pyproject_path = self.project_dir / "pyproject.toml"
        pyproject_path.write_text(content)
        logger.debug(f"Created pyproject.toml: {pyproject_path}")

    def _create_readme(self) -> None:
        """Create the README.md file."""
        content = render_template(self.env, "README.md.j2", self.context)
        readme_path = self.project_dir / "README.md"
        readme_path.write_text(content)
        logger.debug(f"Created README.md: {readme_path}")

    def _create_gitignore(self) -> None:
        """Create the .gitignore file."""
        content = render_template(self.env, "gitignore.j2", self.context)
        gitignore_path = self.project_dir / ".gitignore"
        gitignore_path.write_text(content)
        logger.debug(f"Created .gitignore: {gitignore_path}")

    def _create_github_workflows(self) -> None:
        """Create GitHub Actions workflow files."""
        # Only create workflows if testing or formatting is enabled
        if not self.config.testing.enabled and not self.config.formatting.enabled:
            logger.debug("Skipping GitHub workflows - no testing or formatting enabled")
            return

        workflows_dir = self.project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        ci_template = "github_ci_uv.yaml.j2" if self._is_uv else "github_ci.yaml.j2"
        content = render_template(self.env, ci_template, self.context)
        ci_path = workflows_dir / "ci.yaml"
        ci_path.write_text(content)
        logger.debug(f"Created GitHub CI workflow: {ci_path}")

        # Create dependabot.yml if enabled
        if self.config.dependabot.enabled:
            self._create_dependabot()

    def _create_dependabot(self) -> None:
        """Create the dependabot.yml configuration file."""
        github_dir = self.project_dir / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)

        content = render_template(self.env, "dependabot.yml.j2", self.context)
        dependabot_path = github_dir / "dependabot.yml"
        dependabot_path.write_text(content)
        logger.debug(f"Created dependabot.yml: {dependabot_path}")

    def _create_pre_commit_config(self) -> None:
        """Create .pre-commit-config.yaml for git hooks."""
        content = render_template(self.env, "pre-commit-config.yaml.j2", self.context)
        config_path = self.project_dir / ".pre-commit-config.yaml"
        config_path.write_text(content)
        logger.debug(f"Created .pre-commit-config.yaml: {config_path}")

    def _create_docker_files(self) -> None:
        """Create Dockerfile/Containerfile and ignore file."""
        template = "Dockerfile_uv.j2" if self._is_uv else "Dockerfile.j2"
        content = render_template(self.env, template, self.context)

        if self._is_podman:
            dockerfile_name = "Containerfile"
            ignore_name = ".containerignore"
        else:
            dockerfile_name = "Dockerfile"
            ignore_name = ".dockerignore"

        dockerfile_path = self.project_dir / dockerfile_name
        dockerfile_path.write_text(content)
        logger.debug(f"Created {dockerfile_name}: {dockerfile_path}")

        ignore_content = render_template(self.env, "dockerignore.j2", self.context)
        ignore_path = self.project_dir / ignore_name
        ignore_path.write_text(ignore_content)
        logger.debug(f"Created {ignore_name}: {ignore_path}")

    def _create_devcontainer(self) -> None:
        """Create .devcontainer/devcontainer.json configuration."""
        devcontainer_dir = self.project_dir / ".devcontainer"
        devcontainer_dir.mkdir(parents=True, exist_ok=True)

        content = render_template(self.env, "devcontainer.json.j2", self.context)
        devcontainer_path = devcontainer_dir / "devcontainer.json"
        devcontainer_path.write_text(content)
        logger.debug(f"Created devcontainer.json: {devcontainer_path}")

    def _create_codecov_config(self) -> None:
        """Create codecov.yml configuration."""
        content = render_template(self.env, "codecov.yml.j2", self.context)
        codecov_path = self.project_dir / "codecov.yml"
        codecov_path.write_text(content)
        logger.debug(f"Created codecov.yml: {codecov_path}")

    def _create_documentation(self) -> None:
        """Create documentation scaffolding based on the chosen tool."""
        docs_dir = self.project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        doc_tool = self.config.documentation.tool.value

        if doc_tool == "mkdocs":
            # mkdocs.yml at project root
            config_content = render_template(self.env, "mkdocs.yml.j2", self.context)
            (self.project_dir / "mkdocs.yml").write_text(config_content)
            # docs/index.md
            index_content = render_template(self.env, "docs_index.md.j2", self.context)
            (docs_dir / "index.md").write_text(index_content)
            logger.debug("Created MkDocs documentation scaffolding")
        elif doc_tool == "sphinx":
            # docs/conf.py
            conf_content = render_template(self.env, "sphinx_conf.py.j2", self.context)
            (docs_dir / "conf.py").write_text(conf_content)
            # docs/index.rst
            index_content = render_template(self.env, "docs_index.rst.j2", self.context)
            (docs_dir / "index.rst").write_text(index_content)
            logger.debug("Created Sphinx documentation scaffolding")

        # GitHub Pages deploy workflow
        if self.config.documentation.deploy_gh_pages:
            workflows_dir = self.project_dir / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            workflow_content = render_template(self.env, "docs_workflow.yaml.j2", self.context)
            (workflows_dir / "docs.yaml").write_text(workflow_content)
            logger.debug("Created docs deployment workflow")

    def _create_tox_config(self) -> None:
        """Create tox.ini configuration."""
        content = render_template(self.env, "tox.ini.j2", self.context)
        tox_path = self.project_dir / "tox.ini"
        tox_path.write_text(content)
        logger.debug(f"Created tox.ini: {tox_path}")

    def _render_test_file(self) -> str:
        """Render a basic test file."""
        package_name = self.context["project"]["package_name"]
        return f'''"""Basic tests for {self.config.metadata.name}."""

import {package_name}


def test_version() -> None:
    """Test that version is defined."""
    assert hasattr({package_name}, "__version__")
    assert isinstance({package_name}.__version__, str)


def test_import() -> None:
    """Test that package can be imported."""
    import {package_name}

    assert {package_name} is not None
'''


def generate_project(
    config: ProjectConfig,
    output_dir: Path,
    initialize_git: bool = True,
    install_dependencies: bool = False,
) -> Path:
    """Generate a project from a configuration.

    Args:
        config: The project configuration
        output_dir: Directory to create the project in
        initialize_git: Whether to initialize a git repository
        install_dependencies: Whether to run poetry install

    Returns:
        Path to the generated project directory
    """
    generator = ProjectGenerator(config, output_dir)
    project_dir = generator.generate()

    if initialize_git:
        _init_git(project_dir)

    if install_dependencies:
        is_uv = config.package_manager == CreationPackageManager.UV
        _install_dependencies(project_dir, use_uv=is_uv)

    return project_dir


def _init_git(project_dir: Path) -> None:
    """Initialize a git repository in the project directory."""
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            capture_output=True,
            check=True,
        )
        logger.info("Initialized git repository")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to initialize git repository: {e}")
    except FileNotFoundError:
        logger.warning("git not found, skipping repository initialization")


def _install_dependencies(project_dir: Path, *, use_uv: bool = False) -> None:
    """Run dependency installation in the project directory."""
    cmd = ["uv", "sync"] if use_uv else ["poetry", "install"]
    tool_name = "uv" if use_uv else "poetry"
    try:
        subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            check=True,
        )
        logger.info(f"Installed dependencies with {tool_name}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to install dependencies: {e}")
    except FileNotFoundError:
        logger.warning(f"{tool_name} not found, skipping dependency installation")
