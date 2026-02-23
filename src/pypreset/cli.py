"""CLI interface for pypreset."""

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pypreset.augment_generator import augment_project
from pypreset.generator import generate_project
from pypreset.interactive_prompts import run_auto_session, run_interactive_session
from pypreset.models import (
    CreationPackageManager,
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


def _create_versioning_assistant(project_dir: Path) -> VersioningAssistant:
    return VersioningAssistant(project_dir)


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
        ("Coverage", config.testing.coverage),
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
) -> None:
    """Apply CLI component overrides to an AugmentConfig in place."""
    overrides: list[tuple[str, bool | None]] = [
        ("generate_test_workflow", test_workflow),
        ("generate_lint_workflow", lint_workflow),
        ("generate_dependabot", dependabot),
        ("generate_tests_dir", tests_dir),
        ("generate_gitignore", gitignore),
        ("generate_pypi_publish", pypi_publish),
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
        )

        if not any(
            [
                config.generate_test_workflow,
                config.generate_lint_workflow,
                config.generate_dependabot,
                config.generate_tests_dir,
                config.generate_gitignore,
                config.generate_pypi_publish,
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
) -> None:
    """Bump version, commit, tag, push, and create a GitHub release."""
    project_path = project_dir.absolute()
    try:
        rprint(f"[blue]🚀 Releasing with bump '{bump}'...[/blue]")
        assistant = _create_versioning_assistant(project_path)
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
) -> None:
    """Use an explicit version, then commit, tag, push, and release."""
    project_path = project_dir.absolute()
    try:
        rprint(f"[blue]🚀 Releasing version '{version}'...[/blue]")
        assistant = _create_versioning_assistant(project_path)
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


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
