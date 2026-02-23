"""Interactive prompts for filling in missing configuration."""

import logging
from dataclasses import dataclass
from typing import Any

from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from pypreset.project_analyzer import (
    DetectedLinter,
    DetectedTestFramework,
    DetectedTypeChecker,
    DetectedValue,
    PackageManager,
    ProjectAnalysis,
)

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class AugmentConfig:
    """Configuration for the augment operation."""

    # Project metadata
    project_name: str
    package_name: str
    python_version: str
    description: str

    # Package manager
    package_manager: PackageManager

    # Testing configuration
    test_framework: DetectedTestFramework
    has_coverage: bool

    # Linting configuration
    linter: DetectedLinter
    type_checker: DetectedTypeChecker
    line_length: int

    # Source directories
    source_dirs: list[str]
    has_src_layout: bool

    # What to generate
    generate_test_workflow: bool = True
    generate_lint_workflow: bool = True
    generate_dependabot: bool = True
    generate_tests_dir: bool = True
    generate_gitignore: bool = True
    generate_pypi_publish: bool = False

    # Dependabot settings
    dependabot_schedule: str = "weekly"
    dependabot_pr_limit: int = 5


class InteractivePrompter:
    """Interactive session for collecting missing configuration."""

    def __init__(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        self.confirmed_values: dict[str, Any] = {}

    def display_analysis_summary(self) -> None:
        """Display a summary of what was detected."""
        rprint("\n[bold cyan]📊 Project Analysis Summary[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Detected Value")
        table.add_column("Confidence")
        table.add_column("Source")

        detections: list[tuple[str, DetectedValue[Any] | None]] = [
            ("Project Name", self.analysis.project_name),
            ("Package Name", self.analysis.package_name),
            ("Version", self.analysis.version),
            ("Python Version", self.analysis.python_version),
            ("Package Manager", self.analysis.package_manager),
            ("Test Framework", self.analysis.test_framework),
            ("Linter", self.analysis.linter),
            ("Type Checker", self.analysis.type_checker),
            ("Line Length", self.analysis.line_length),
        ]

        for name, detection in detections:
            if detection is not None:
                value = detection.value
                if hasattr(value, "value"):  # Enum
                    value = value.value

                confidence_style = {
                    "high": "[green]high[/green]",
                    "medium": "[yellow]medium[/yellow]",
                    "low": "[red]low[/red]",
                }.get(detection.confidence, detection.confidence)

                table.add_row(name, str(value), confidence_style, detection.source)
            else:
                table.add_row(name, "[dim]Not detected[/dim]", "[red]none[/red]", "-")

        console.print(table)

        # Show existing structure
        rprint("\n[bold cyan]📁 Project Structure[/bold cyan]")
        rprint(f"  • Has src/ layout: {'✓' if self.analysis.has_src_layout else '✗'}")
        rprint(f"  • Has tests/ directory: {'✓' if self.analysis.has_tests_dir else '✗'}")
        rprint(f"  • Has .github/ directory: {'✓' if self.analysis.has_github_dir else '✗'}")
        rprint(f"  • Has dependabot.yml: {'✓' if self.analysis.has_dependabot else '✗'}")
        rprint(f"  • Has .gitignore: {'✓' if self.analysis.has_gitignore else '✗'}")

        if self.analysis.existing_workflows:
            rprint(f"  • Existing workflows: {[w.name for w in self.analysis.existing_workflows]}")

        if self.analysis.existing_tests:
            rprint(f"  • Existing tests: {len(self.analysis.existing_tests)} files")

    def prompt_for_missing_fields(self) -> dict[str, Any]:
        """Prompt user for missing fields."""
        if not self.analysis.missing_fields:
            return {}

        rprint(
            "\n[bold yellow]⚠️ Some configuration could not be detected."
            " Please provide:[/bold yellow]\n"
        )

        results: dict[str, Any] = {}

        for field in self.analysis.missing_fields:
            if field.choices:
                # Use choices prompt
                choices_str = ", ".join(field.choices)
                default_display = f" [{field.default}]" if field.default else ""
                value = Prompt.ask(
                    f"  {field.description} ({choices_str}){default_display}",
                    default=field.default,
                    choices=field.choices,
                )
            else:
                # Free text prompt
                default_display = f" [{field.default}]" if field.default else ""
                value = Prompt.ask(
                    f"  {field.description}{default_display}",
                    default=field.default or "",
                )

            results[field.name] = value

        return results

    def prompt_for_confirmation(self) -> dict[str, Any]:
        """Prompt user to confirm uncertain detected values."""
        uncertain = self.analysis.get_uncertain_values()

        if not uncertain:
            return {}

        rprint("\n[bold yellow]🔍 Please confirm these detected values:[/bold yellow]\n")

        results: dict[str, Any] = {}

        for name, detection in uncertain.items():
            value = detection.value
            display_value = value.value if hasattr(value, "value") else str(value)

            confirmed = Confirm.ask(
                f"  {name}: [cyan]{display_value}[/cyan] (from {detection.source})?",
                default=True,
            )

            if confirmed:
                results[name] = detection.value
            else:
                # Allow user to provide alternative
                new_value = Prompt.ask(f"  Enter new value for {name}")
                results[name] = new_value

        return results

    def prompt_for_components(self) -> dict[str, bool]:
        """Prompt user for which components to generate."""
        rprint("\n[bold cyan]🛠️ Select components to generate:[/bold cyan]\n")

        components: dict[str, bool] = {}

        # Test workflow
        if self.analysis.existing_workflows:
            has_test_workflow = any(
                "test" in w.name.lower() or "ci" in w.name.lower()
                for w in self.analysis.existing_workflows
            )
            if has_test_workflow:
                rprint("  [dim]Test workflow already exists[/dim]")
                components["generate_test_workflow"] = Confirm.ask(
                    "  Overwrite existing test workflow?",
                    default=False,
                )
            else:
                components["generate_test_workflow"] = Confirm.ask(
                    "  Generate test workflow?",
                    default=True,
                )
        else:
            components["generate_test_workflow"] = Confirm.ask(
                "  Generate test workflow?",
                default=True,
            )

        # Lint workflow
        has_lint_workflow = any("lint" in w.name.lower() for w in self.analysis.existing_workflows)
        if has_lint_workflow:
            rprint("  [dim]Lint workflow already exists[/dim]")
            components["generate_lint_workflow"] = Confirm.ask(
                "  Overwrite existing lint workflow?",
                default=False,
            )
        else:
            components["generate_lint_workflow"] = Confirm.ask(
                "  Generate lint workflow?",
                default=True,
            )

        # Dependabot
        if self.analysis.has_dependabot:
            rprint("  [dim]dependabot.yml already exists[/dim]")
            components["generate_dependabot"] = Confirm.ask(
                "  Overwrite existing dependabot.yml?",
                default=False,
            )
        else:
            components["generate_dependabot"] = Confirm.ask(
                "  Generate dependabot.yml?",
                default=True,
            )

        # Tests directory
        if self.analysis.has_tests_dir and self.analysis.existing_tests:
            test_count = len(self.analysis.existing_tests)
            rprint(f"  [dim]tests/ directory exists with {test_count} test files[/dim]")
            components["generate_tests_dir"] = Confirm.ask(
                "  Generate template test file? (will not overwrite existing)",
                default=False,
            )
        elif self.analysis.has_tests_dir:
            components["generate_tests_dir"] = Confirm.ask(
                "  Generate template test file in tests/?",
                default=True,
            )
        else:
            components["generate_tests_dir"] = Confirm.ask(
                "  Create tests/ directory with template test?",
                default=True,
            )

        # Gitignore
        if self.analysis.has_gitignore:
            rprint("  [dim].gitignore already exists[/dim]")
            components["generate_gitignore"] = Confirm.ask(
                "  Overwrite existing .gitignore?",
                default=False,
            )
        else:
            components["generate_gitignore"] = Confirm.ask(
                "  Generate .gitignore?",
                default=True,
            )

        return components

    def prompt_for_dependabot_config(self) -> dict[str, Any]:
        """Prompt for dependabot configuration if enabled."""
        rprint("\n[bold cyan]📦 Dependabot Configuration:[/bold cyan]\n")

        schedule = Prompt.ask(
            "  Update schedule (daily, weekly, monthly)",
            default="weekly",
            choices=["daily", "weekly", "monthly"],
        )

        pr_limit = Prompt.ask(
            "  Maximum open pull requests",
            default="5",
        )

        return {
            "dependabot_schedule": schedule,
            "dependabot_pr_limit": int(pr_limit),
        }

    def build_augment_config(self, interactive: bool = True) -> AugmentConfig:
        """Build augment configuration through interactive prompts or auto-detection."""
        # Display analysis summary
        if interactive:
            self.display_analysis_summary()

        # Collect missing fields
        if interactive and self.analysis.missing_fields:
            missing_values = self.prompt_for_missing_fields()
        else:
            missing_values = {}

        # Confirm uncertain values
        confirmed_values = self.prompt_for_confirmation() if interactive else {}

        # Select components to generate
        if interactive:
            components = self.prompt_for_components()
        else:
            components = {
                "generate_test_workflow": True,
                "generate_lint_workflow": True,
                "generate_dependabot": not self.analysis.has_dependabot,
                "generate_tests_dir": not self.analysis.has_tests_dir,
                "generate_gitignore": not self.analysis.has_gitignore,
                "generate_pypi_publish": False,
            }

        # Dependabot configuration
        if components.get("generate_dependabot", False) and interactive:
            dependabot_config = self.prompt_for_dependabot_config()
        else:
            dependabot_config = {"dependabot_schedule": "weekly", "dependabot_pr_limit": 5}

        # Build the final config
        return self._build_config(missing_values, confirmed_values, components, dependabot_config)

    def _build_config(
        self,
        missing_values: dict[str, Any],
        confirmed_values: dict[str, Any],
        components: dict[str, bool],
        dependabot_config: dict[str, Any],
    ) -> AugmentConfig:
        """Build AugmentConfig from collected values."""

        # Helper to get value with priority: confirmed > missing > detected
        def get_value(name: str, default: Any = None) -> Any:
            if name in confirmed_values:
                return confirmed_values[name]
            if name in missing_values:
                return missing_values[name]

            detected = getattr(self.analysis, name, None)
            if detected is not None and isinstance(detected, DetectedValue):
                return detected.value
            return default

        # Get test framework
        test_framework_value = get_value("test_framework", DetectedTestFramework.PYTEST)
        if isinstance(test_framework_value, str):
            test_framework = DetectedTestFramework(test_framework_value)
        else:
            test_framework = test_framework_value

        # Get linter
        linter_value = get_value("linter", DetectedLinter.RUFF)
        linter = DetectedLinter(linter_value) if isinstance(linter_value, str) else linter_value

        # Get type checker
        type_checker_value = get_value("type_checker", DetectedTypeChecker.MYPY)
        if isinstance(type_checker_value, str):
            type_checker = DetectedTypeChecker(type_checker_value)
        else:
            type_checker = type_checker_value

        # Get package manager
        package_manager_value = get_value("package_manager", PackageManager.POETRY)
        if isinstance(package_manager_value, str):
            package_manager = PackageManager(package_manager_value)
        else:
            package_manager = package_manager_value

        return AugmentConfig(
            project_name=get_value("project_name", "my-project"),
            package_name=get_value("package_name", "my_project"),
            python_version=get_value("python_version", "3.11"),
            description=get_value("description", ""),
            package_manager=package_manager,
            test_framework=test_framework,
            has_coverage="pytest-cov" in self.analysis.dev_dependencies
            or "coverage" in self.analysis.dev_dependencies,
            linter=linter,
            type_checker=type_checker,
            line_length=get_value("line_length", 100),
            source_dirs=self.analysis.source_dirs or ["src"],
            has_src_layout=self.analysis.has_src_layout,
            generate_test_workflow=components.get("generate_test_workflow", True),
            generate_lint_workflow=components.get("generate_lint_workflow", True),
            generate_dependabot=components.get("generate_dependabot", True),
            generate_tests_dir=components.get("generate_tests_dir", True),
            generate_gitignore=components.get("generate_gitignore", True),
            generate_pypi_publish=components.get("generate_pypi_publish", False),
            dependabot_schedule=dependabot_config.get("dependabot_schedule", "weekly"),
            dependabot_pr_limit=dependabot_config.get("dependabot_pr_limit", 5),
        )


def run_interactive_session(analysis: ProjectAnalysis) -> AugmentConfig:
    """Run an interactive session to collect configuration."""
    prompter = InteractivePrompter(analysis)
    return prompter.build_augment_config(interactive=True)


def run_auto_session(analysis: ProjectAnalysis) -> AugmentConfig:
    """Build configuration automatically without prompts."""
    prompter = InteractivePrompter(analysis)
    return prompter.build_augment_config(interactive=False)
