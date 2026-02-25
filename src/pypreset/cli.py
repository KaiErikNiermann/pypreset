"""CLI interface for pypreset."""

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pypreset.augment_generator import augment_project
from pypreset.generator import generate_project
from pypreset.interactive_prompts import run_auto_session, run_interactive_session
from pypreset.models import (
    ContainerRuntime,
    CoverageTool,
    CreationPackageManager,
    DocumentationTool,
    LayoutStyle,
    OverrideOptions,
    TypeChecker,
    TypingLevel,
)
from pypreset.preset_loader import (
    build_project_config,
    list_available_presets,
    load_preset,
    resolve_preset_chain,
)
from pypreset.project_analyzer import analyze_project
from pypreset.user_config import (
    get_config_path,
    get_default_config_template,
    load_user_config,
    save_user_config,
)
from pypreset.validator import validate_project, validate_with_poetry
from pypreset.versioning import VersioningAssistant, VersioningError

if TYPE_CHECKING:
    from pypreset.augment_generator import AugmentResult
    from pypreset.interactive_prompts import AugmentConfig
    from pypreset.models import ProjectConfig

app = typer.Typer(
    name="pypreset",
    help="A meta-tool for setting up Poetry-based Python projects with configurable presets.",
    no_args_is_help=True,
)

version_app = typer.Typer(
    name="version",
    help="Versioning assistance commands.",
    no_args_is_help=True,
)

app.add_typer(version_app, name="version")

metadata_app = typer.Typer(
    name="metadata",
    help="Read, set, and check PyPI metadata in pyproject.toml.",
    no_args_is_help=True,
)
app.add_typer(metadata_app, name="metadata")

workflow_app = typer.Typer(
    name="workflow",
    help="Workflow verification commands.",
    no_args_is_help=True,
)
app.add_typer(workflow_app, name="workflow")

config_app = typer.Typer(
    name="config",
    help="Manage user-level default preferences.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _create_versioning_assistant(
    project_dir: Path,
    *,
    server_file: Path | None = None,
) -> VersioningAssistant:
    return VersioningAssistant(project_dir, server_file=server_file)


def _warn_metadata(project_dir: Path) -> None:
    """Show publish-readiness warnings for project metadata."""
    import tomllib

    from pypreset.metadata_utils import check_publish_readiness

    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    warnings = check_publish_readiness(data)
    if warnings:
        rprint("\n[dim]PyPI metadata hints (run 'pypreset metadata set' to fix):[/dim]")
        for w in warnings:
            rprint(f"  [dim]- {w}[/dim]")


@app.command("create")
def create_project(
    name: Annotated[str, typer.Argument(help="Name of the project to create")],
    preset: Annotated[
        str, typer.Option("--preset", "-p", help="Preset to use for project setup")
    ] = "empty-package",
    output_dir: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory for the project")
    ] = Path("."),
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Custom preset config file")
    ] = None,
    testing: Annotated[
        bool | None, typer.Option("--testing/--no-testing", help="Enable/disable testing")
    ] = None,
    formatting: Annotated[
        bool | None,
        typer.Option("--formatting/--no-formatting", help="Enable/disable formatting"),
    ] = None,
    python_version: Annotated[
        str | None, typer.Option("--python-version", help="Python version (e.g., 3.11)")
    ] = None,
    typing_level: Annotated[
        TypingLevel | None,
        typer.Option("--typing", help="Typing strictness level"),
    ] = None,
    layout: Annotated[
        LayoutStyle | None,
        typer.Option("--layout", help="Project layout style (src or flat)"),
    ] = None,
    radon: Annotated[
        bool | None,
        typer.Option("--radon/--no-radon", help="Enable radon complexity checking"),
    ] = None,
    pre_commit: Annotated[
        bool | None,
        typer.Option("--pre-commit/--no-pre-commit", help="Generate pre-commit hooks config"),
    ] = None,
    version_bumping: Annotated[
        bool | None,
        typer.Option(
            "--bump-my-version/--no-bump-my-version",
            help="Include bump-my-version for version management",
        ),
    ] = None,
    type_checker: Annotated[
        TypeChecker | None,
        typer.Option("--type-checker", help="Type checker (mypy, pyright, or ty)"),
    ] = None,
    package_manager: Annotated[
        CreationPackageManager | None,
        typer.Option("--package-manager", help="Package manager (poetry or uv)"),
    ] = None,
    docker: Annotated[
        bool | None,
        typer.Option("--docker/--no-docker", help="Generate Dockerfile and .dockerignore"),
    ] = None,
    devcontainer: Annotated[
        bool | None,
        typer.Option(
            "--devcontainer/--no-devcontainer", help="Generate .devcontainer/ configuration"
        ),
    ] = None,
    container_runtime: Annotated[
        ContainerRuntime | None,
        typer.Option("--container-runtime", help="Container runtime (docker or podman)"),
    ] = None,
    coverage_tool: Annotated[
        CoverageTool | None,
        typer.Option("--coverage-tool", help="Coverage service (codecov or none)"),
    ] = None,
    coverage_threshold: Annotated[
        int | None,
        typer.Option("--coverage-threshold", help="Minimum coverage percentage"),
    ] = None,
    docs: Annotated[
        DocumentationTool | None,
        typer.Option("--docs", help="Documentation tool (sphinx, mkdocs, or none)"),
    ] = None,
    docs_gh_pages: Annotated[
        bool | None,
        typer.Option("--docs-gh-pages/--no-docs-gh-pages", help="Deploy docs to GitHub Pages"),
    ] = None,
    tox: Annotated[
        bool | None,
        typer.Option("--tox/--no-tox", help="Generate tox.ini with tox-uv"),
    ] = None,
    extra_package: Annotated[
        list[str] | None,
        typer.Option("--extra-package", "-e", help="Additional packages to install"),
    ] = None,
    extra_dev_package: Annotated[
        list[str] | None,
        typer.Option("--extra-dev-package", "-d", help="Additional dev packages"),
    ] = None,
    init_git: Annotated[
        bool, typer.Option("--git/--no-git", help="Initialize git repository")
    ] = True,
    install: Annotated[
        bool, typer.Option("--install/--no-install", help="Run dependency install")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview what would be created without generating anything"),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Create a new Python project from a preset."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build override options
    # Determine coverage_enabled from coverage_tool
    coverage_enabled = True if coverage_tool and coverage_tool != CoverageTool.NONE else None

    # Determine docs_enabled from docs tool
    docs_enabled = True if docs and docs != DocumentationTool.NONE else None

    overrides = OverrideOptions(
        testing_enabled=testing,
        formatting_enabled=formatting,
        radon_enabled=radon,
        pre_commit_enabled=pre_commit,
        version_bumping_enabled=version_bumping,
        type_checker=type_checker,
        python_version=python_version,
        typing_level=typing_level,
        layout=layout,
        package_manager=package_manager,
        docker_enabled=docker,
        devcontainer_enabled=devcontainer,
        container_runtime=container_runtime,
        coverage_enabled=coverage_enabled,
        coverage_tool=coverage_tool,
        coverage_threshold=coverage_threshold,
        docs_enabled=docs_enabled,
        docs_tool=docs,
        docs_deploy_gh_pages=docs_gh_pages,
        tox_enabled=tox,
        extra_packages=extra_package or [],
        extra_dev_packages=extra_dev_package or [],
    )

    try:
        # Build project configuration
        project_config = build_project_config(
            project_name=name,
            preset_name=preset,
            overrides=overrides,
            custom_preset_path=config,
        )

        if dry_run:
            _display_dry_run(name, preset, output_dir.absolute(), project_config, init_git, install)
            return

        rprint(f"[blue]Creating project '{name}' with preset '{preset}'...[/blue]")

        # Generate the project
        project_dir = generate_project(
            config=project_config,
            output_dir=output_dir.absolute(),
            initialize_git=init_git,
            install_dependencies=install,
        )

        # Validate the generated project
        is_valid, results = validate_project(project_dir)

        if is_valid:
            rprint(
                Panel.fit(
                    f"[green]✓ Project '{name}' created successfully![/green]\n\n"
                    f"Location: [cyan]{project_dir}[/cyan]\n\n"
                    f"[dim]Next steps:[/dim]\n"
                    f"  cd {name}\n"
                    f"  poetry install\n"
                    f"  poetry run pytest",
                    title="Success",
                )
            )
        else:
            rprint("[yellow]Project created with warnings:[/yellow]")
            for result in results:
                if not result.passed:
                    rprint(f"  [yellow]⚠ {result.message}[/yellow]")

        # Warn about incomplete PyPI metadata
        _warn_metadata(project_dir)

    except ValueError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1) from None


def _display_dry_run(
    name: str,
    preset: str,
    output_dir: Path,
    config: "ProjectConfig",
    init_git: bool,
    install: bool,
) -> None:
    """Display a dry-run summary of what would be created."""
    from pypreset.models import CreationPackageManager, LayoutStyle
    from pypreset.template_engine import render_path

    package_name = name.replace("-", "_")
    is_src = config.layout == LayoutStyle.SRC
    is_uv = config.package_manager == CreationPackageManager.UV
    project_dir = output_dir / name
    context = {"project": {"name": name, "package_name": package_name}}

    # --- Header ---
    rprint(
        Panel.fit(
            "[bold]Dry run[/bold] — nothing will be created",
            title=f"pypreset create {name} --preset {preset}",
            border_style="yellow",
        )
    )

    # --- Project overview ---
    overview = Table(title="Project Overview", show_header=False, box=None, padding=(0, 2))
    overview.add_column(style="cyan")
    overview.add_column()
    overview.add_row("Location", str(project_dir))
    overview.add_row("Preset", preset)
    overview.add_row("Package manager", config.package_manager.value)
    overview.add_row("Layout", config.layout.value)
    overview.add_row("Python", config.metadata.python_version)
    overview.add_row(
        "Typing", f"{config.typing_level.value} ({config.formatting.type_checker.value})"
    )
    overview.add_row(
        "Testing", config.testing.framework.value if config.testing.enabled else "disabled"
    )
    overview.add_row(
        "Formatting", config.formatting.tool.value if config.formatting.enabled else "disabled"
    )
    overview.add_row("Git init", "yes" if init_git else "no")
    overview.add_row("Install deps", "yes" if install else "no")
    console.print(overview)
    rprint()

    # --- Feature flags ---
    flags: list[tuple[str, bool]] = [
        ("Radon complexity", config.formatting.radon),
        ("Pre-commit hooks", config.formatting.pre_commit),
        ("bump-my-version", config.formatting.version_bumping),
        ("Dependabot", config.dependabot.enabled),
        ("Coverage", config.testing.coverage_config.enabled),
        ("Docker", config.docker.enabled),
        ("Devcontainer", config.docker.devcontainer),
        ("Documentation", config.documentation.enabled),
        ("tox", config.tox.enabled),
    ]
    active = [name for name, enabled in flags if enabled]
    if active:
        rprint(f"[cyan]Extras:[/cyan] {', '.join(active)}")
        rprint()

    # --- Directory tree ---
    tree_lines: list[str] = []
    pkg_prefix = f"src/{package_name}" if is_src else package_name

    tree_lines.append(f"{name}/")
    tree_lines.append(f"  {pkg_prefix}/")
    tree_lines.append("    __init__.py")

    # Preset-defined directories
    for dir_path in config.structure.directories:
        rendered = render_path(dir_path, context)
        tree_lines.append(f"  {rendered}/")

    # Preset-defined files
    for file_def in config.structure.files:
        rendered = render_path(file_def.path, context)
        tree_lines.append(f"  {rendered}")

    if config.testing.enabled:
        tree_lines.append("  tests/")
        tree_lines.append("    __init__.py")
        tree_lines.append("    test_basic.py")

    pyproject_tmpl = "pyproject_uv.toml" if is_uv else "pyproject.toml"
    tree_lines.append(f"  {pyproject_tmpl.replace('_uv', '')} [dim]({pyproject_tmpl}.j2)[/dim]")
    tree_lines.append("  README.md")
    tree_lines.append("  .gitignore")

    if config.testing.enabled or config.formatting.enabled:
        ci_tmpl = "github_ci_uv.yaml" if is_uv else "github_ci.yaml"
        tree_lines.append(f"  .github/workflows/ci.yaml [dim]({ci_tmpl}.j2)[/dim]")

    if config.dependabot.enabled:
        tree_lines.append("  .github/dependabot.yml")

    if config.formatting.pre_commit:
        tree_lines.append("  .pre-commit-config.yaml")

    if config.docker.enabled:
        tree_lines.append("  Dockerfile")
        tree_lines.append("  .dockerignore")

    if config.docker.devcontainer:
        tree_lines.append("  .devcontainer/")
        tree_lines.append("    devcontainer.json")

    if (
        config.testing.coverage_config.enabled
        and config.testing.coverage_config.tool.value == "codecov"
    ):
        tree_lines.append("  codecov.yml")

    if config.documentation.enabled:
        doc_tool = config.documentation.tool.value
        if doc_tool == "mkdocs":
            tree_lines.append("  mkdocs.yml")
            tree_lines.append("  docs/")
            tree_lines.append("    index.md")
        elif doc_tool == "sphinx":
            tree_lines.append("  docs/")
            tree_lines.append("    conf.py")
            tree_lines.append("    index.rst")
        if config.documentation.deploy_gh_pages:
            tree_lines.append("  .github/workflows/docs.yaml")

    if config.tox.enabled:
        tree_lines.append("  tox.ini")

    rprint(Panel("\n".join(tree_lines), title="Project Structure", border_style="green"))

    # --- Dependencies ---
    if config.dependencies.main or config.dependencies.dev:
        dep_table = Table(title="Dependencies")
        dep_table.add_column("Package", style="white")
        dep_table.add_column("Group", style="dim")

        for pkg in config.dependencies.main:
            dep_table.add_row(pkg, "main")
        for pkg in config.dependencies.dev:
            dep_table.add_row(pkg, "dev")

        console.print(dep_table)

    # --- Entry points ---
    if config.entry_points:
        rprint("\n[cyan]Entry points:[/cyan]")
        for ep in config.entry_points:
            rprint(f"  {ep.name} = {ep.module}")


@app.command("list-presets")
def list_presets_cmd() -> None:
    """List all available presets."""
    presets = list_available_presets()

    if not presets:
        rprint("[yellow]No presets found.[/yellow]")
        return

    table = Table(title="Available Presets")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name, description in presets:
        table.add_row(name, description)

    console.print(table)


@app.command("show-preset")
def show_preset_cmd(
    preset_name: Annotated[str, typer.Argument(help="Name of the preset to show")],
) -> None:
    """Show details of a specific preset."""
    try:
        preset = load_preset(preset_name)
        resolved = resolve_preset_chain(preset)

        rprint(
            Panel.fit(
                f"[bold]{preset.name}[/bold]\n\n[dim]{preset.description}[/dim]",
                title="Preset Info",
            )
        )

        if preset.base:
            rprint(f"\n[cyan]Extends:[/cyan] {preset.base}")

        # Show dependencies
        deps = resolved.get("dependencies", {})
        if deps.get("main"):
            rprint("\n[cyan]Dependencies:[/cyan]")
            for pkg in deps["main"]:
                rprint(f"  • {pkg}")

        if deps.get("dev"):
            rprint("\n[cyan]Dev Dependencies:[/cyan]")
            for pkg in deps["dev"]:
                rprint(f"  • {pkg}")

        # Show structure
        structure = resolved.get("structure", {})
        if structure.get("directories"):
            rprint("\n[cyan]Directories:[/cyan]")
            for dir_path in structure["directories"]:
                rprint(f"  📁 {dir_path}")

        if structure.get("files"):
            rprint("\n[cyan]Files:[/cyan]")
            for file_info in structure["files"]:
                path = file_info.get("path", "unknown")
                rprint(f"  📄 {path}")

        # Show entry points
        entry_points = resolved.get("entry_points", [])
        if entry_points:
            rprint("\n[cyan]Entry Points:[/cyan]")
            for ep in entry_points:
                rprint(f"  • {ep['name']} → {ep['module']}")

    except ValueError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("validate")
def validate_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project to validate")] = Path(
        "."
    ),
    poetry_check: Annotated[
        bool, typer.Option("--poetry/--no-poetry", help="Also run poetry check")
    ] = False,
) -> None:
    """Validate an existing project."""
    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    rprint(f"[blue]Validating project at {project_path}...[/blue]\n")

    is_valid, results = validate_project(project_path)

    for result in results:
        if result.passed:
            rprint(f"  [green]✓[/green] {result.message}")
        else:
            rprint(f"  [red]✗[/red] {result.message}")

    if poetry_check:
        rprint("\n[blue]Running poetry check...[/blue]")
        poetry_result = validate_with_poetry(project_path)
        if poetry_result.passed:
            rprint(f"  [green]✓[/green] {poetry_result.message}")
        else:
            rprint(f"  [red]✗[/red] {poetry_result.message}")
            if poetry_result.details:
                rprint(f"    [dim]{poetry_result.details}[/dim]")

    if is_valid:
        rprint("\n[green]All validations passed![/green]")
    else:
        rprint("\n[red]Some validations failed.[/red]")
        raise typer.Exit(1)


def _apply_component_overrides(
    config: "AugmentConfig",
    *,
    test_workflow: bool | None,
    lint_workflow: bool | None,
    dependabot: bool | None,
    tests_dir: bool | None,
    gitignore: bool | None,
    pypi_publish: bool | None,
    dockerfile_flag: bool | None = None,
    devcontainer_flag: bool | None = None,
) -> None:
    """Apply CLI component overrides to an AugmentConfig in place."""
    overrides: list[tuple[str, bool | None]] = [
        ("generate_test_workflow", test_workflow),
        ("generate_lint_workflow", lint_workflow),
        ("generate_dependabot", dependabot),
        ("generate_tests_dir", tests_dir),
        ("generate_gitignore", gitignore),
        ("generate_pypi_publish", pypi_publish),
        ("generate_dockerfile", dockerfile_flag),
        ("generate_devcontainer", devcontainer_flag),
    ]
    for attr, value in overrides:
        if value is not None:
            setattr(config, attr, value)


def _display_augment_result(result: "AugmentResult") -> None:
    """Print augment operation results and raise on errors."""
    if result.files_created:
        rprint("\n[green]✓ Created files:[/green]")
        for file in result.files_created:
            status = "[yellow](overwritten)[/yellow]" if file.overwritten else ""
            rprint(f"  • {file.path} {status}")

    if result.files_skipped:
        rprint("\n[yellow]⚠ Skipped files (already exist):[/yellow]")
        for path in result.files_skipped:
            rprint(f"  • {path}")

    if result.errors:
        rprint("\n[red]✗ Errors:[/red]")
        for error in result.errors:
            rprint(f"  • {error}")
        raise typer.Exit(1)

    if result.success:
        rprint(
            Panel.fit(
                "[green]✓ Project augmented successfully![/green]\n\n"
                f"[dim]Generated {len(result.files_created)} file(s)[/dim]",
                title="Success",
            )
        )
    else:
        rprint("\n[yellow]Project augmented with warnings.[/yellow]")


@app.command("augment")
def augment_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project to augment")] = Path("."),
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive/--auto",
            "-i/-a",
            help="Interactive mode for missing values (default) or auto-detect everything",
        ),
    ] = True,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files"),
    ] = False,
    test_workflow: Annotated[
        bool | None,
        typer.Option("--test-workflow/--no-test-workflow", help="Generate test workflow"),
    ] = None,
    lint_workflow: Annotated[
        bool | None,
        typer.Option("--lint-workflow/--no-lint-workflow", help="Generate lint workflow"),
    ] = None,
    dependabot: Annotated[
        bool | None,
        typer.Option("--dependabot/--no-dependabot", help="Generate dependabot.yml"),
    ] = None,
    tests_dir: Annotated[
        bool | None,
        typer.Option("--tests/--no-tests", help="Generate tests directory"),
    ] = None,
    gitignore: Annotated[
        bool | None,
        typer.Option("--gitignore/--no-gitignore", help="Generate .gitignore file"),
    ] = None,
    pypi_publish: Annotated[
        bool | None,
        typer.Option("--pypi-publish/--no-pypi-publish", help="Generate PyPI publish workflow"),
    ] = None,
    dockerfile: Annotated[
        bool | None,
        typer.Option("--dockerfile/--no-dockerfile", help="Generate Dockerfile and .dockerignore"),
    ] = None,
    devcontainer_flag: Annotated[
        bool | None,
        typer.Option(
            "--devcontainer/--no-devcontainer", help="Generate .devcontainer/ configuration"
        ),
    ] = None,
    codecov: Annotated[
        bool | None,
        typer.Option("--codecov/--no-codecov", help="Generate codecov.yml"),
    ] = None,
    augment_docs: Annotated[
        str | None,
        typer.Option("--docs", help="Generate documentation scaffolding (sphinx or mkdocs)"),
    ] = None,
    augment_tox: Annotated[
        bool | None,
        typer.Option("--tox/--no-tox", help="Generate tox.ini"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Augment an existing project with workflows, tests, and configuration.

    Analyzes your pyproject.toml and project structure to automatically generate:
    - GitHub Actions test workflow
    - GitHub Actions lint workflow
    - Dependabot configuration
    - Tests directory with template tests
    - .gitignore file

    If information cannot be reliably detected, an interactive prompt will ask
    for the missing details. Use --auto to skip prompts and use detected/default values.

    Examples:
        pypreset augment                    # Augment current directory
        pypreset augment ./my-project       # Augment specific project
        pypreset augment --auto             # Auto-detect everything, no prompts
        pypreset augment --force            # Overwrite existing files
        pypreset augment --test-workflow    # Only generate test workflow
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        rprint(f"[red]Error: No pyproject.toml found in '{project_path}'[/red]")
        rprint(
            "[dim]The augment command requires an existing Python project with pyproject.toml[/dim]"
        )
        raise typer.Exit(1)

    try:
        # Analyze the project
        rprint(f"[blue]🔍 Analyzing project at {project_path}...[/blue]")
        analysis = analyze_project(project_path)

        # Build augment configuration
        if interactive:
            config = run_interactive_session(analysis)
        else:
            config = run_auto_session(analysis)
            rprint("\n[cyan]📋 Auto-detected configuration:[/cyan]")
            rprint(f"  • Project: [bold]{config.project_name}[/bold]")
            rprint(f"  • Python: {config.python_version}")
            rprint(f"  • Package Manager: {config.package_manager.value}")
            rprint(f"  • Test Framework: {config.test_framework.value}")
            rprint(f"  • Linter: {config.linter.value}")
            rprint(f"  • Type Checker: {config.type_checker.value}")

        _apply_component_overrides(
            config,
            test_workflow=test_workflow,
            lint_workflow=lint_workflow,
            dependabot=dependabot,
            tests_dir=tests_dir,
            gitignore=gitignore,
            pypi_publish=pypi_publish,
            dockerfile_flag=dockerfile,
            devcontainer_flag=devcontainer_flag,
        )

        # Apply new augment overrides
        if codecov is not None:
            config.generate_codecov = codecov
        if augment_tox is not None:
            config.generate_tox = augment_tox
        if augment_docs is not None:
            config.generate_documentation = True
            config.documentation_tool = augment_docs

        if not any(
            [
                config.generate_test_workflow,
                config.generate_lint_workflow,
                config.generate_dependabot,
                config.generate_tests_dir,
                config.generate_gitignore,
                config.generate_pypi_publish,
                config.generate_dockerfile,
                config.generate_devcontainer,
                config.generate_codecov,
                config.generate_documentation,
                config.generate_tox,
            ]
        ):
            rprint("[yellow]No components selected for generation.[/yellow]")
            raise typer.Exit(0)

        rprint("\n[blue]🛠️  Generating components...[/blue]")
        result = augment_project(project_path, config, force=force)
        _display_augment_result(result)

    except KeyboardInterrupt:
        rprint("\n[yellow]Augment cancelled.[/yellow]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1) from None


@version_app.command("release")
def release_cmd(
    bump: Annotated[
        str,
        typer.Option(
            "--bump",
            "-b",
            help="Version bump (patch, minor, major, prerelease, etc.)",
        ),
    ] = "patch",
    project_dir: Annotated[
        Path, typer.Option("--path", "-p", help="Path to the project root")
    ] = Path("."),
    server_file: Annotated[
        Path | None,
        typer.Option(
            "--server-file",
            help="[experimental] Path to MCP server JSON file to sync version into",
        ),
    ] = None,
) -> None:
    """Bump version, commit, tag, push, and create a GitHub release."""
    project_path = project_dir.absolute()
    resolved_server = server_file.absolute() if server_file else None
    try:
        rprint(f"[blue]🚀 Releasing with bump '{bump}'...[/blue]")
        assistant = _create_versioning_assistant(project_path, server_file=resolved_server)
        version = assistant.release(bump)
        rprint(
            Panel.fit(
                f"[green]✓ Release v{version} created.[/green]",
                title="Release",
            )
        )
    except VersioningError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@version_app.command("release-version")
def release_version_cmd(
    version: Annotated[str, typer.Argument(help="Explicit version to release")],
    project_dir: Annotated[
        Path, typer.Option("--path", "-p", help="Path to the project root")
    ] = Path("."),
    server_file: Annotated[
        Path | None,
        typer.Option(
            "--server-file",
            help="[experimental] Path to MCP server JSON file to sync version into",
        ),
    ] = None,
) -> None:
    """Use an explicit version, then commit, tag, push, and release."""
    project_path = project_dir.absolute()
    resolved_server = server_file.absolute() if server_file else None
    try:
        rprint(f"[blue]🚀 Releasing version '{version}'...[/blue]")
        assistant = _create_versioning_assistant(project_path, server_file=resolved_server)
        normalized = assistant.release_version(version)
        rprint(
            Panel.fit(
                f"[green]✓ Release v{normalized} created.[/green]",
                title="Release",
            )
        )
    except VersioningError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@version_app.command("rerun")
def rerun_cmd(
    version: Annotated[str, typer.Argument(help="Version to re-tag and push")],
    project_dir: Annotated[
        Path, typer.Option("--path", "-p", help="Path to the project root")
    ] = Path("."),
) -> None:
    """Re-tag and push an existing version."""
    project_path = project_dir.absolute()
    try:
        rprint(f"[blue]🔁 Re-tagging and pushing '{version}'...[/blue]")
        assistant = _create_versioning_assistant(project_path)
        normalized = assistant.rerun(version)
        rprint(
            Panel.fit(
                f"[green]✓ Re-tagged v{normalized}.[/green]",
                title="Re-run",
            )
        )
    except VersioningError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@version_app.command("rerelease")
def rerelease_cmd(
    version: Annotated[str, typer.Argument(help="Version to delete and recreate")],
    project_dir: Annotated[
        Path, typer.Option("--path", "-p", help="Path to the project root")
    ] = Path("."),
) -> None:
    """Delete and recreate the GitHub release for a version."""
    project_path = project_dir.absolute()
    try:
        rprint(f"[blue]♻️  Recreating GitHub release '{version}'...[/blue]")
        assistant = _create_versioning_assistant(project_path)
        normalized = assistant.rerelease(version)
        rprint(
            Panel.fit(
                f"[green]✓ Recreated release v{normalized}.[/green]",
                title="Re-release",
            )
        )
    except VersioningError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command("analyze")
def analyze_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project to analyze")] = Path("."),
) -> None:
    """Analyze an existing project and display detected configuration.

    This is useful to preview what the augment command would detect
    before actually generating any files.
    """
    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        rprint(f"[red]Error: No pyproject.toml found in '{project_path}'[/red]")
        raise typer.Exit(1)

    rprint(f"[blue]🔍 Analyzing project at {project_path}...[/blue]\n")
    analysis = analyze_project(project_path)

    # Display analysis using the interactive prompter's display method
    from pypreset.interactive_prompts import InteractivePrompter

    prompter = InteractivePrompter(analysis)
    prompter.display_analysis_summary()


@metadata_app.command("show")
def metadata_show_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project")] = Path("."),
) -> None:
    """Show current PyPI metadata from pyproject.toml."""
    from pypreset.metadata_utils import read_pyproject_metadata

    project_path = project_dir.absolute()
    try:
        meta = read_pyproject_metadata(project_path)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None

    table = Table(title="Project Metadata")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    for key, value in meta.items():
        display = str(value) if value else "[dim]<empty>[/dim]"
        table.add_row(key, display)

    console.print(table)


@metadata_app.command("set")
def metadata_set_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project")] = Path("."),
    description: Annotated[
        str | None, typer.Option("--description", help="Package description")
    ] = None,
    authors: Annotated[
        list[str] | None, typer.Option("--author", help="Author (repeatable)")
    ] = None,
    license_id: Annotated[
        str | None, typer.Option("--license", help="SPDX license identifier")
    ] = None,
    keywords: Annotated[
        list[str] | None, typer.Option("--keyword", help="Keyword (repeatable)")
    ] = None,
    repository_url: Annotated[
        str | None, typer.Option("--repository-url", help="Source repository URL")
    ] = None,
    homepage_url: Annotated[
        str | None, typer.Option("--homepage-url", help="Project homepage URL")
    ] = None,
    documentation_url: Annotated[
        str | None, typer.Option("--documentation-url", help="Documentation site URL")
    ] = None,
    bug_tracker_url: Annotated[
        str | None, typer.Option("--bug-tracker-url", help="Issue tracker URL")
    ] = None,
    github_owner: Annotated[
        str | None,
        typer.Option("--github-owner", help="GitHub owner/org — auto-generates URLs"),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", "-f", help="Overwrite existing non-empty values")
    ] = False,
) -> None:
    """Set or update PyPI metadata in pyproject.toml.

    By default, only fills in empty/unset fields. Use --overwrite to replace
    existing values.

    Examples:
        pypreset metadata set --description "My awesome package"
        pypreset metadata set --github-owner myuser
        pypreset metadata set --license MIT --keyword python --keyword cli
    """
    from pypreset.metadata_utils import (
        generate_default_urls,
        read_pyproject_metadata,
        set_pyproject_metadata,
    )

    project_path = project_dir.absolute()

    try:
        current = read_pyproject_metadata(project_path)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None

    # Build updates
    updates: dict[str, Any] = {}
    if description is not None:
        updates["description"] = description
    if authors is not None:
        updates["authors"] = authors
    if license_id is not None:
        updates["license"] = license_id
    if keywords is not None:
        updates["keywords"] = keywords
    if repository_url is not None:
        updates["repository_url"] = repository_url
    if homepage_url is not None:
        updates["homepage_url"] = homepage_url
    if documentation_url is not None:
        updates["documentation_url"] = documentation_url
    if bug_tracker_url is not None:
        updates["bug_tracker_url"] = bug_tracker_url

    # Auto-generate URLs from github_owner
    if github_owner:
        auto_urls = generate_default_urls(current["name"], github_owner)
        for key, value in auto_urls.items():
            updates.setdefault(key, value)

    if not updates:
        rprint("[yellow]No metadata fields specified. Use --help to see options.[/yellow]")
        raise typer.Exit(1)

    try:
        warnings = set_pyproject_metadata(project_path, updates, overwrite=overwrite)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None

    rprint(f"[green]Updated {len(updates)} field(s) in pyproject.toml[/green]")
    for field in updates:
        rprint(f"  [cyan]{field}[/cyan] = {updates[field]}")

    if warnings:
        rprint("\n[yellow]Publish-readiness warnings:[/yellow]")
        for w in warnings:
            rprint(f"  [yellow]! {w}[/yellow]")


@metadata_app.command("check")
def metadata_check_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project")] = Path("."),
) -> None:
    """Check if metadata is ready for PyPI publishing.

    Reports warnings for empty, placeholder, or missing metadata fields
    that should be filled before publishing to PyPI.
    """
    import tomllib

    from pypreset.metadata_utils import check_publish_readiness

    project_path = project_dir.absolute()
    pyproject_path = project_path / "pyproject.toml"

    if not pyproject_path.exists():
        rprint(f"[red]Error: No pyproject.toml found in {project_path}[/red]")
        raise typer.Exit(1)

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    warnings = check_publish_readiness(data)

    if warnings:
        rprint("[yellow]Metadata is not ready for publishing:[/yellow]\n")
        for w in warnings:
            rprint(f"  [yellow]! {w}[/yellow]")
        rprint("\n[dim]Use 'pypreset metadata set' to fill in missing fields.[/dim]")
        raise typer.Exit(1)
    else:
        rprint("[green]All metadata fields look good for publishing![/green]")


@config_app.command("show")
def config_show_cmd() -> None:
    """Show current user configuration."""
    config_path = get_config_path()
    user_cfg = load_user_config()

    if not user_cfg:
        rprint(f"[yellow]No user config found at {config_path}[/yellow]")
        rprint("[dim]Run 'pypreset config init' to create one.[/dim]")
        return

    rprint(f"[cyan]Config file:[/cyan] {config_path}\n")
    table = Table(title="User Defaults")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    for key, value in user_cfg.items():
        table.add_row(key, str(value))

    console.print(table)


@config_app.command("init")
def config_init_cmd(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing config")] = False,
) -> None:
    """Create a default user configuration file."""
    config_path = get_config_path()

    if config_path.exists() and not force:
        rprint(f"[yellow]Config already exists at {config_path}[/yellow]")
        rprint("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    template = get_default_config_template()
    saved_path = save_user_config(template)
    rprint(f"[green]Created default config at {saved_path}[/green]")
    rprint("[dim]Edit this file to customize your defaults.[/dim]")


@config_app.command("set")
def config_set_cmd(
    key: Annotated[str, typer.Argument(help="Config key to set")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a single configuration value."""
    user_cfg = load_user_config()

    # Try to coerce numeric values
    coerced: str | int = value
    with contextlib.suppress(ValueError):
        coerced = int(value)

    user_cfg[key] = coerced
    save_user_config(user_cfg)
    rprint(f"[green]Set {key} = {coerced}[/green]")


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the path to the user config file."""
    rprint(str(get_config_path()))


@workflow_app.command("verify")
def workflow_verify_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project root")] = Path("."),
    workflow_file: Annotated[
        str | None,
        typer.Option("--workflow", "-w", help="Specific workflow file (relative to project)"),
    ] = None,
    job: Annotated[
        str | None,
        typer.Option("--job", "-j", help="Specific job to verify"),
    ] = None,
    event: Annotated[
        str,
        typer.Option("--event", "-e", help="GitHub event to simulate"),
    ] = "push",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--full-run",
            help="Dry-run (validate only) or full run (execute in containers)",
        ),
    ] = True,
    platform_map: Annotated[
        str | None,
        typer.Option("--platform", help="Platform mapping (e.g. 'ubuntu-latest=image:tag')"),
    ] = None,
    auto_install: Annotated[
        bool,
        typer.Option("--auto-install/--no-auto-install", help="Auto-install act if missing"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", "-t", help="Timeout in seconds for act commands"),
    ] = 600,
    extra_flags: Annotated[
        list[str] | None,
        typer.Option("--flag", "-f", help="Extra flags to pass to act (repeatable)"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify GitHub Actions workflows locally using act.

    Checks if act is installed, optionally installs it, then runs
    workflow verification. Surfaces all act output directly.

    Examples:
        pypreset workflow verify                          # Verify all workflows (dry-run)
        pypreset workflow verify --workflow .github/workflows/ci.yaml
        pypreset workflow verify --job lint               # Verify specific job
        pypreset workflow verify --full-run               # Run workflows in containers
        pypreset workflow verify --auto-install           # Install act if missing
        pypreset workflow verify --flag="--secret=FOO=bar"
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    from pypreset.act_runner import verify_workflow

    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    rprint(f"[blue]Verifying workflows in {project_path}...[/blue]")

    wf_path = Path(workflow_file) if workflow_file else None

    result = verify_workflow(
        project_dir=project_path,
        workflow_file=wf_path,
        job=job,
        event=event,
        dry_run=dry_run,
        platform_map=platform_map,
        extra_flags=extra_flags or None,
        timeout=timeout,
        auto_install=auto_install,
    )

    # Display act status
    if result.act_available:
        rprint(f"  [green]act available:[/green] {result.act_version}")
    else:
        rprint("  [red]act not available[/red]")

    # Display warnings
    for warning in result.warnings:
        rprint(f"  [yellow]{warning}[/yellow]")

    # Display run results
    for run in result.runs:
        cmd_str = " ".join(run.command)
        if run.success:
            rprint(f"\n  [green]PASS[/green] {cmd_str}")
        else:
            rprint(f"\n  [red]FAIL[/red] {cmd_str}")

        if run.stdout.strip():
            rprint(f"[dim]{run.stdout.strip()}[/dim]")
        if run.stderr.strip():
            rprint(f"[dim]{run.stderr.strip()}[/dim]")

    # Display errors
    if result.errors:
        rprint("\n[red]Errors:[/red]")
        for error in result.errors:
            rprint(f"  [red]- {error}[/red]")
        raise typer.Exit(1)

    rprint("\n[green]Workflow verification passed.[/green]")


@workflow_app.command("check-act")
def workflow_check_act_cmd() -> None:
    """Check if act is installed and show install suggestions."""
    from pypreset.act_runner import check_act, get_install_suggestion

    check = check_act()

    if check.installed:
        rprint(f"[green]act is installed:[/green] {check.version}")
    else:
        rprint(f"[red]act is not installed:[/red] {check.error}")
        suggestion, _ = get_install_suggestion()
        rprint(f"\n[cyan]Suggestion:[/cyan] {suggestion}")


@workflow_app.command("install-act")
def workflow_install_act_cmd() -> None:
    """Attempt to install act automatically."""
    from pypreset.act_runner import check_act, install_act

    check = check_act()
    if check.installed:
        rprint(f"[green]act is already installed:[/green] {check.version}")
        return

    rprint("[blue]Attempting to install act...[/blue]")
    result = install_act()

    if result.success:
        rprint(f"[green]{result.message}[/green]")
    else:
        rprint(f"[red]{result.message}[/red]")
        raise typer.Exit(1)


@app.command("migrate")
def migrate_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project to migrate")] = Path("."),
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--no-dry-run", help="Preview changes without modifying files"),
    ] = False,
    skip_lock: Annotated[
        bool,
        typer.Option("--skip-lock/--no-skip-lock", help="Skip locking dependencies with uv"),
    ] = False,
    skip_uv_checks: Annotated[
        bool,
        typer.Option(
            "--skip-uv-checks/--no-skip-uv-checks",
            help="Skip checks for whether project already uses uv",
        ),
    ] = False,
    ignore_locked_versions: Annotated[
        bool,
        typer.Option(
            "--ignore-locked-versions/--no-ignore-locked-versions",
            help="Ignore current locked dependency versions",
        ),
    ] = False,
    replace_project_section: Annotated[
        bool,
        typer.Option(
            "--replace-project-section/--no-replace-project-section",
            help="Replace existing [project] section instead of keeping existing fields",
        ),
    ] = False,
    keep_current_build_backend: Annotated[
        bool,
        typer.Option(
            "--keep-current-build-backend/--no-keep-current-build-backend",
            help="Keep the current build backend",
        ),
    ] = False,
    keep_current_data: Annotated[
        bool,
        typer.Option(
            "--keep-current-data/--no-keep-current-data",
            help="Keep data from current package manager (don't delete old files)",
        ),
    ] = False,
    ignore_errors: Annotated[
        bool,
        typer.Option(
            "--ignore-errors/--no-ignore-errors",
            help="Continue migration even if errors occur",
        ),
    ] = False,
    package_manager: Annotated[
        str | None,
        typer.Option(
            "--package-manager",
            "-p",
            help="Source package manager (poetry/pipenv/pip-tools/pip). Auto-detected if omitted",
        ),
    ] = None,
    dependency_groups_strategy: Annotated[
        str | None,
        typer.Option(
            "--dependency-groups-strategy",
            help="Strategy for migrating dependency groups",
        ),
    ] = None,
    build_backend: Annotated[
        str | None,
        typer.Option("--build-backend", help="Build backend to use (hatch, uv)"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Migrate a project to uv using migrate-to-uv.

    Wraps the upstream migrate-to-uv tool (https://github.com/mkniewallner/migrate-to-uv)
    to migrate projects from Poetry, Pipenv, pip-tools, or pip to uv.

    Examples:
        pypreset migrate                            # Migrate current directory
        pypreset migrate ./my-project               # Migrate specific project
        pypreset migrate --dry-run                   # Preview changes
        pypreset migrate --package-manager poetry    # Force Poetry detection
        pypreset migrate --keep-current-data         # Don't delete old files
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    from pypreset.migration import (
        MigrationCommandFailure,
        MigrationError,
        MigrationOptions,
        check_migrate_to_uv,
        migrate_to_uv,
    )

    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    available, version = check_migrate_to_uv()
    if not available:
        rprint(
            "[red]Error: migrate-to-uv is not installed.[/red]\n"
            "Install it with: [cyan]pip install migrate-to-uv[/cyan]  "
            "or: [cyan]uvx migrate-to-uv[/cyan]"
        )
        raise typer.Exit(1)

    rprint(f"[blue]Using migrate-to-uv {version or '(unknown version)'}[/blue]")
    action = "Previewing migration" if dry_run else "Migrating"
    rprint(f"[blue]{action} project at {project_path}...[/blue]")

    opts = MigrationOptions(
        project_dir=project_path,
        dry_run=dry_run,
        skip_lock=skip_lock,
        skip_uv_checks=skip_uv_checks,
        ignore_locked_versions=ignore_locked_versions,
        replace_project_section=replace_project_section,
        keep_current_build_backend=keep_current_build_backend,
        keep_current_data=keep_current_data,
        ignore_errors=ignore_errors,
        package_manager=package_manager,  # type: ignore[arg-type]
        dependency_groups_strategy=dependency_groups_strategy,  # type: ignore[arg-type]
        build_backend=build_backend,  # type: ignore[arg-type]
    )

    try:
        result = migrate_to_uv(opts)
    except MigrationCommandFailure as exc:
        rprint(f"[red]Migration failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    except MigrationError as exc:
        rprint(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    if result.stdout.strip():
        rprint(result.stdout.strip())
    if result.stderr.strip():
        rprint(f"[yellow]{result.stderr.strip()}[/yellow]")

    if result.success:
        if dry_run:
            rprint("[green]Dry-run complete — no files were modified.[/green]")
        else:
            rprint("[green]Migration to uv completed successfully![/green]")
    else:
        rprint("[yellow]Migration completed with warnings (--ignore-errors was set).[/yellow]")


@app.command("tree")
def tree_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project root")] = Path("."),
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Maximum directory depth"),
    ] = 3,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: text (default) or json",
        ),
    ] = "text",
) -> None:
    """Print an intelligent project tree structure.

    Automatically hides noise like __pycache__, .git, node_modules,
    .venv, dist, build, and other non-essential directories.

    Examples:
        pypreset tree                      # Current directory, depth 3
        pypreset tree ./my-project -d 2    # Custom path and depth
        pypreset tree --format json        # JSON output for scripting
    """
    import json

    from pypreset.inspect import project_tree

    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        rprint(f"[red]Error: '{project_path}' is not a directory[/red]")
        raise typer.Exit(1)

    tree = project_tree(project_path, max_depth=depth)

    match output_format:
        case "json":
            rprint(json.dumps({"project": project_path.name, "tree": tree}))
        case _:
            rprint(tree)


@app.command("deps")
def deps_cmd(
    project_dir: Annotated[Path, typer.Argument(help="Path to the project root")] = Path("."),
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: table (default), json, or csv",
        ),
    ] = "table",
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="Filter by group (main, dev, etc.)"),
    ] = None,
) -> None:
    """Extract dependencies with names and versions.

    Reads pyproject.toml (Poetry, PEP 621, uv/hatch, PDM, flit),
    requirements*.txt, requirements*.in, and Pipfile. Outputs clean,
    manipulatable name + version fields.

    Examples:
        pypreset deps                          # Table of all deps
        pypreset deps --format json            # JSON for scripting / CI
        pypreset deps --format csv             # CSV for spreadsheets
        pypreset deps --group dev              # Only dev dependencies
        pypreset deps ./other-project          # Inspect another project
    """
    import json

    from pypreset.inspect import extract_dependencies

    project_path = project_dir.absolute()

    if not project_path.exists():
        rprint(f"[red]Error: Directory '{project_path}' does not exist[/red]")
        raise typer.Exit(1)

    deps = extract_dependencies(project_path)

    if group:
        deps = [d for d in deps if d.group == group]

    if not deps:
        rprint("[yellow]No dependencies found.[/yellow]")
        return

    match output_format:
        case "json":
            rprint(json.dumps([d.to_dict() for d in deps], indent=2))
        case "csv":
            rprint("name,version,group,extras,source")
            for d in deps:
                extras_str = ";".join(d.extras) if d.extras else ""
                rprint(f"{d.name},{d.version},{d.group},{extras_str},{d.source}")
        case _:
            table = Table(title="Dependencies")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Group", style="yellow")
            table.add_column("Source", style="dim")
            for d in deps:
                name = d.name
                if d.extras:
                    name += f"[{','.join(d.extras)}]"
                table.add_row(name, d.version, d.group, d.source)
            Console().print(table)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
