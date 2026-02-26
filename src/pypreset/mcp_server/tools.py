"""MCP tool handlers — actions an AI assistant can invoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

if TYPE_CHECKING:
    from fastmcp import FastMCP

from pypreset.models import (
    ContainerRuntime,  # noqa: F401
    CoverageTool,  # noqa: F401
    CreationPackageManager,
    DocumentationTool,  # noqa: F401
    LayoutStyle,
    OverrideOptions,
    TypeChecker,
    TypingLevel,
)


def register_tools(mcp: FastMCP) -> None:
    """Register all tool handlers on the given MCP server."""

    # ------------------------------------------------------------------
    # create_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="create_project",
        description=(
            "Create a new Python project from a preset. "
            "Returns the path to the generated project directory."
        ),
        tags={"project", "create"},
    )
    def create_project(
        project_name: Annotated[str, Field(description="Name for the new project (e.g. 'my-app')")],
        preset: Annotated[
            str, Field(description="Preset name (e.g. 'empty-package', 'cli-tool', 'data-science')")
        ],
        output_dir: Annotated[str, Field(description="Directory to create the project in")] = ".",
        initialize_git: Annotated[bool, Field(description="Initialize a git repository")] = True,
        install_dependencies: Annotated[
            bool, Field(description="Run package manager install after generation")
        ] = False,
        layout: Annotated[
            str | None, Field(description="Layout style override: 'src' or 'flat'")
        ] = None,
        type_checker: Annotated[
            str | None,
            Field(description="Type checker override: 'mypy', 'pyright', 'ty', or 'none'"),
        ] = None,
        package_manager: Annotated[
            str | None, Field(description="Package manager override: 'poetry' or 'uv'")
        ] = None,
        typing_level: Annotated[
            str | None,
            Field(description="Typing strictness override: 'none', 'basic', or 'strict'"),
        ] = None,
        python_version: Annotated[
            str | None, Field(description="Python version override (e.g. '3.12')")
        ] = None,
        docker: Annotated[bool, Field(description="Generate Dockerfile and .dockerignore")] = False,
        devcontainer: Annotated[
            bool, Field(description="Generate .devcontainer/ configuration")
        ] = False,
        container_runtime: Annotated[
            str | None,
            Field(description="Container runtime: 'docker' or 'podman'"),
        ] = None,
        docs: Annotated[
            str | None,
            Field(description="Documentation tool: 'sphinx', 'mkdocs', or 'none'"),
        ] = None,
        docs_gh_pages: Annotated[
            bool, Field(description="Generate GitHub Pages deploy workflow for docs")
        ] = False,
        tox: Annotated[bool, Field(description="Generate tox.ini with tox-uv")] = False,
        coverage_tool: Annotated[
            str | None,
            Field(description="Coverage service: 'codecov' or 'none'"),
        ] = None,
        coverage_threshold: Annotated[
            int | None,
            Field(description="Minimum coverage percentage"),
        ] = None,
    ) -> str:
        from pypreset.generator import generate_project
        from pypreset.preset_loader import build_project_config

        # Derive docs_enabled from docs param
        docs_enabled = True if docs and docs != "none" else None

        # Derive coverage_enabled from coverage_tool param
        coverage_enabled = True if coverage_tool and coverage_tool != "none" else None

        overrides = OverrideOptions(
            testing_enabled=None,
            formatting_enabled=None,
            radon_enabled=None,
            pre_commit_enabled=None,
            version_bumping_enabled=None,
            layout=LayoutStyle(layout) if layout else None,
            type_checker=TypeChecker(type_checker) if type_checker else None,
            package_manager=CreationPackageManager(package_manager) if package_manager else None,
            typing_level=TypingLevel(typing_level) if typing_level else None,
            python_version=python_version,
            docker_enabled=docker if docker else None,
            devcontainer_enabled=devcontainer if devcontainer else None,
            container_runtime=ContainerRuntime(container_runtime) if container_runtime else None,
            coverage_enabled=coverage_enabled,
            coverage_tool=CoverageTool(coverage_tool) if coverage_tool else None,
            coverage_threshold=coverage_threshold,
            docs_enabled=docs_enabled,
            docs_tool=DocumentationTool(docs) if docs else None,
            docs_deploy_gh_pages=docs_gh_pages if docs_gh_pages else None,
            tox_enabled=tox if tox else None,
        )

        config = build_project_config(
            project_name=project_name,
            preset_name=preset,
            overrides=overrides,
        )

        project_path = generate_project(
            config=config,
            output_dir=Path(output_dir),
            initialize_git=initialize_git,
            install_dependencies=install_dependencies,
        )

        return json.dumps(
            {
                "project_dir": str(project_path),
                "project_name": project_name,
                "preset": preset,
                "layout": config.layout.value,
                "package_manager": config.package_manager.value,
                "docker_enabled": config.docker.enabled,
                "devcontainer_enabled": config.docker.devcontainer,
                "container_runtime": config.docker.container_runtime.value,
                "documentation_enabled": config.documentation.enabled,
                "documentation_tool": config.documentation.tool.value,
                "tox_enabled": config.tox.enabled,
                "coverage_enabled": config.testing.coverage_config.enabled,
                "coverage_tool": config.testing.coverage_config.tool.value,
            }
        )

    # ------------------------------------------------------------------
    # validate_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="validate_project",
        description="Validate the structural correctness of a generated project directory.",
        tags={"project", "validate"},
    )
    def validate_project(
        project_dir: Annotated[str, Field(description="Path to the project directory to validate")],
    ) -> str:
        from pypreset.validator import validate_project as _validate

        is_valid, results = _validate(Path(project_dir))

        return json.dumps(
            {
                "valid": is_valid,
                "checks": [
                    {
                        "passed": r.passed,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in results
                ],
            }
        )

    # ------------------------------------------------------------------
    # list_presets
    # ------------------------------------------------------------------
    @mcp.tool(
        name="list_presets",
        description="List all available project presets with their descriptions.",
        tags={"preset"},
    )
    def list_presets() -> str:
        from pypreset.preset_loader import list_available_presets

        presets = list_available_presets()
        return json.dumps([{"name": name, "description": desc} for name, desc in presets])

    # ------------------------------------------------------------------
    # show_preset
    # ------------------------------------------------------------------
    @mcp.tool(
        name="show_preset",
        description="Show the full configuration of a specific preset.",
        tags={"preset"},
    )
    def show_preset(
        preset_name: Annotated[str, Field(description="Name of the preset to show")],
    ) -> str:
        from pypreset.preset_loader import load_preset

        preset = load_preset(preset_name)
        return json.dumps(preset.model_dump(exclude_none=True), default=str)

    # ------------------------------------------------------------------
    # get_user_config
    # ------------------------------------------------------------------
    @mcp.tool(
        name="get_user_config",
        description="Read the current user-level default configuration.",
        tags={"config"},
    )
    def get_user_config() -> str:
        from pypreset.user_config import get_config_path, load_user_config

        config = load_user_config()
        return json.dumps(
            {
                "config_path": str(get_config_path()),
                "values": config,
            }
        )

    # ------------------------------------------------------------------
    # set_user_config
    # ------------------------------------------------------------------
    @mcp.tool(
        name="set_user_config",
        description=(
            "Update user-level default configuration values. "
            "Merges provided keys into existing config."
        ),
        tags={"config"},
    )
    def set_user_config(
        values: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Key-value pairs to set (e.g. {'layout': 'src', 'python_version': '3.12'})"
                )
            ),
        ],
    ) -> str:
        from pypreset.user_config import load_user_config, save_user_config

        current = load_user_config()
        current.update(values)
        path = save_user_config(current)
        return json.dumps({"config_path": str(path), "values": current})

    # ------------------------------------------------------------------
    # augment_project
    # ------------------------------------------------------------------
    @mcp.tool(
        name="augment_project",
        description=(
            "Add CI workflows, tests, gitignore, and/or dependabot to an existing project. "
            "Analyzes the project first, then generates selected components."
        ),
        tags={"project", "augment"},
    )
    def augment_project(
        project_dir: Annotated[str, Field(description="Path to the existing project directory")],
        force: Annotated[bool, Field(description="Overwrite existing files if they exist")] = False,
        generate_test_workflow: Annotated[
            bool, Field(description="Generate test CI workflow")
        ] = True,
        generate_lint_workflow: Annotated[
            bool, Field(description="Generate lint CI workflow")
        ] = True,
        generate_dependabot: Annotated[bool, Field(description="Generate dependabot.yml")] = True,
        generate_tests_dir: Annotated[bool, Field(description="Generate tests directory")] = True,
        generate_gitignore: Annotated[bool, Field(description="Generate .gitignore")] = True,
        generate_dockerfile: Annotated[
            bool, Field(description="Generate Dockerfile and .dockerignore")
        ] = False,
        generate_devcontainer: Annotated[
            bool, Field(description="Generate .devcontainer/ configuration")
        ] = False,
        generate_codecov: Annotated[bool, Field(description="Generate codecov.yml")] = False,
        generate_documentation: Annotated[
            bool, Field(description="Generate documentation scaffolding")
        ] = False,
        documentation_tool: Annotated[
            str, Field(description="Documentation tool: 'sphinx' or 'mkdocs'")
        ] = "sphinx",
        generate_tox: Annotated[bool, Field(description="Generate tox.ini")] = False,
        generate_readme: Annotated[
            bool, Field(description="Generate README.md from template")
        ] = False,
    ) -> str:
        from pypreset.augment_generator import augment_project as _augment
        from pypreset.interactive_prompts import InteractivePrompter
        from pypreset.project_analyzer import analyze_project

        path = Path(project_dir)
        analysis = analyze_project(path)

        # Build config non-interactively
        prompter = InteractivePrompter(analysis)
        config = prompter.build_augment_config(interactive=False)

        # Override component selections
        config.generate_test_workflow = generate_test_workflow
        config.generate_lint_workflow = generate_lint_workflow
        config.generate_dependabot = generate_dependabot
        config.generate_tests_dir = generate_tests_dir
        config.generate_gitignore = generate_gitignore
        config.generate_dockerfile = generate_dockerfile
        config.generate_devcontainer = generate_devcontainer
        config.generate_codecov = generate_codecov
        config.generate_documentation = generate_documentation
        config.documentation_tool = documentation_tool
        config.generate_tox = generate_tox
        config.generate_readme = generate_readme

        result = _augment(project_dir=path, config=config, force=force)

        return json.dumps(
            {
                "success": result.success,
                "files_created": [
                    {"path": str(f.path), "overwritten": f.overwritten}
                    for f in result.files_created
                ],
                "files_skipped": [str(p) for p in result.files_skipped],
                "errors": result.errors,
            }
        )

    # ------------------------------------------------------------------
    # verify_workflow
    # ------------------------------------------------------------------
    @mcp.tool(
        name="verify_workflow",
        description=(
            "Verify GitHub Actions workflows locally using act. "
            "Checks if act is installed (warns if not — do NOT assume it is), "
            "optionally auto-installs it on supported Linux distros, "
            "then runs the workflow in dry-run or full mode. "
            "All act output and errors are surfaced directly. "
            "Some workflows cannot be tested locally (e.g. those needing "
            "GitHub-specific secrets or contexts) — this is expected."
        ),
        tags={"workflow", "verify", "act"},
    )
    def verify_workflow(
        project_dir: Annotated[str, Field(description="Path to the project root directory")],
        workflow_file: Annotated[
            str | None,
            Field(
                description=(
                    "Specific workflow file relative to project (e.g. '.github/workflows/ci.yaml')"
                )
            ),
        ] = None,
        job: Annotated[
            str | None,
            Field(description="Specific job name to verify (runs all jobs if omitted)"),
        ] = None,
        event: Annotated[
            str, Field(description="GitHub event to simulate (default: 'push')")
        ] = "push",
        dry_run: Annotated[
            bool, Field(description="Validate without executing containers (default: true)")
        ] = True,
        platform_map: Annotated[
            str | None,
            Field(
                description="Platform mapping (e.g. 'ubuntu-latest=catthehacker/ubuntu:act-latest')"
            ),
        ] = None,
        extra_flags: Annotated[
            list[str] | None,
            Field(description="Additional flags to pass through to act"),
        ] = None,
        timeout: Annotated[
            int, Field(description="Timeout in seconds for act commands (default: 600)")
        ] = 600,
        auto_install: Annotated[
            bool,
            Field(description="Attempt to auto-install act if not found (default: false)"),
        ] = False,
    ) -> str:
        from pypreset.act_runner import verify_workflow as _verify

        wf_path = Path(workflow_file) if workflow_file else None

        result = _verify(
            project_dir=Path(project_dir),
            workflow_file=wf_path,
            job=job,
            event=event,
            dry_run=dry_run,
            platform_map=platform_map,
            extra_flags=extra_flags,
            timeout=timeout,
            auto_install=auto_install,
        )

        return json.dumps(
            {
                "act_available": result.act_available,
                "act_version": result.act_version,
                "workflow_path": result.workflow_path,
                "errors": result.errors,
                "warnings": result.warnings,
                "runs": [
                    {
                        "success": run.success,
                        "command": run.command,
                        "stdout": run.stdout,
                        "stderr": run.stderr,
                        "return_code": run.return_code,
                    }
                    for run in result.runs
                ],
            }
        )

    # ------------------------------------------------------------------
    # set_project_metadata
    # ------------------------------------------------------------------
    @mcp.tool(
        name="set_project_metadata",
        description=(
            "Set or update PyPI metadata (description, authors, license, URLs, keywords) "
            "in an existing project's pyproject.toml. Only updates fields that are currently "
            "empty unless overwrite=True. Returns publish-readiness warnings for any "
            "fields that are still empty or using placeholder defaults."
        ),
        tags={"project", "metadata"},
    )
    def set_project_metadata(
        project_dir: Annotated[str, Field(description="Path to the project directory")],
        description: Annotated[
            str | None, Field(description="Short package description for PyPI")
        ] = None,
        authors: Annotated[
            list[str] | None,
            Field(description="Authors list, e.g. ['Name <email@example.com>']"),
        ] = None,
        license: Annotated[
            str | None, Field(description="SPDX license identifier (e.g. 'MIT', 'Apache-2.0')")
        ] = None,
        keywords: Annotated[list[str] | None, Field(description="PyPI search keywords")] = None,
        classifiers: Annotated[
            list[str] | None,
            Field(description="PyPI trove classifiers"),
        ] = None,
        repository_url: Annotated[str | None, Field(description="Source repository URL")] = None,
        homepage_url: Annotated[str | None, Field(description="Project homepage URL")] = None,
        documentation_url: Annotated[
            str | None, Field(description="Documentation site URL")
        ] = None,
        bug_tracker_url: Annotated[str | None, Field(description="Issue/bug tracker URL")] = None,
        github_owner: Annotated[
            str | None,
            Field(
                description=(
                    "GitHub owner/org name — auto-generates repository, homepage, "
                    "and bug tracker URLs from this (e.g. 'myuser' or 'myorg')"
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Overwrite existing non-empty values (default: only fill blanks)"),
        ] = False,
    ) -> str:
        from pypreset.metadata_utils import (
            generate_default_urls,
            read_pyproject_metadata,
            set_pyproject_metadata,
        )

        path = Path(project_dir)

        # Read current metadata to get project name for URL generation
        current = read_pyproject_metadata(path)

        # Build updates dict from non-None arguments
        updates: dict[str, Any] = {}
        if description is not None:
            updates["description"] = description
        if authors is not None:
            updates["authors"] = authors
        if license is not None:
            updates["license"] = license
        if keywords is not None:
            updates["keywords"] = keywords
        if classifiers is not None:
            updates["classifiers"] = classifiers
        if repository_url is not None:
            updates["repository_url"] = repository_url
        if homepage_url is not None:
            updates["homepage_url"] = homepage_url
        if documentation_url is not None:
            updates["documentation_url"] = documentation_url
        if bug_tracker_url is not None:
            updates["bug_tracker_url"] = bug_tracker_url

        # Auto-generate URLs from github_owner if provided
        if github_owner:
            auto_urls = generate_default_urls(current["name"], github_owner)
            for key, value in auto_urls.items():
                updates.setdefault(key, value)

        warnings = set_pyproject_metadata(path, updates, overwrite=overwrite)

        return json.dumps(
            {
                "updated_fields": list(updates.keys()),
                "warnings": warnings,
                "metadata": read_pyproject_metadata(path),
            }
        )

    @mcp.tool(
        name="migrate_to_uv",
        description=(
            "Migrate a Python project to uv from another package manager "
            "(Poetry, Pipenv, pip-tools, or pip) using the upstream migrate-to-uv tool. "
            "Requires migrate-to-uv to be installed (pip install migrate-to-uv). "
            "All upstream output and errors are surfaced directly."
        ),
        tags={"migration", "uv", "package-manager"},
    )
    def migrate_to_uv_tool(
        project_dir: Annotated[str, Field(description="Path to the project to migrate")],
        dry_run: Annotated[
            bool, Field(description="Preview changes without modifying files (default: false)")
        ] = False,
        skip_lock: Annotated[
            bool,
            Field(description="Skip locking dependencies with uv after migration (default: false)"),
        ] = False,
        skip_uv_checks: Annotated[
            bool,
            Field(
                description=("Skip checks for whether the project already uses uv (default: false)")
            ),
        ] = False,
        ignore_locked_versions: Annotated[
            bool,
            Field(description="Ignore current locked dependency versions (default: false)"),
        ] = False,
        replace_project_section: Annotated[
            bool,
            Field(
                description=(
                    "Replace existing [project] section instead of keeping "
                    "existing fields (default: false)"
                )
            ),
        ] = False,
        keep_current_build_backend: Annotated[
            bool,
            Field(description="Keep the current build backend (default: false)"),
        ] = False,
        keep_current_data: Annotated[
            bool,
            Field(
                description=(
                    "Keep data from current package manager — "
                    "don't delete old files/sections (default: false)"
                )
            ),
        ] = False,
        ignore_errors: Annotated[
            bool,
            Field(description="Continue migration even if errors occur (default: false)"),
        ] = False,
        package_manager: Annotated[
            str | None,
            Field(
                description=(
                    "Source package manager: 'poetry', 'pipenv', 'pip-tools', or 'pip'. "
                    "Auto-detected if omitted"
                )
            ),
        ] = None,
        dependency_groups_strategy: Annotated[
            str | None,
            Field(
                description=(
                    "Strategy for migrating dependency groups: "
                    "'set-default-groups-all', 'set-default-groups', "
                    "'include-in-dev', 'keep-existing', 'merge-into-dev'"
                )
            ),
        ] = None,
        build_backend: Annotated[
            str | None,
            Field(description="Build backend to use: 'hatch' or 'uv'"),
        ] = None,
    ) -> str:
        from pypreset.migration import (
            MigrationCommandFailure,
            MigrationError,
            MigrationOptions,
            check_migrate_to_uv,
            migrate_to_uv,
        )

        available, version = check_migrate_to_uv()
        if not available:
            return json.dumps(
                {
                    "success": False,
                    "error": (
                        "migrate-to-uv is not installed. Install it with: pip install migrate-to-uv"
                    ),
                }
            )

        opts = MigrationOptions(
            project_dir=Path(project_dir),
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
            return json.dumps(
                {
                    "success": False,
                    "error": str(exc),
                    "command": exc.command,
                    "return_code": exc.returncode,
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                }
            )
        except MigrationError as exc:
            return json.dumps({"success": False, "error": str(exc)})

        return json.dumps(
            {
                "success": result.success,
                "dry_run": result.dry_run,
                "migrate_to_uv_version": version,
                "command": result.command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
            }
        )

    @mcp.tool(
        name="project_tree",
        description=(
            "Print an intelligent project tree structure. "
            "Automatically hides noise like __pycache__, .git, node_modules, "
            ".venv, dist, build, and other non-essential directories."
        ),
        tags={"inspect", "tree", "structure"},
    )
    def project_tree_tool(
        project_dir: Annotated[str, Field(description="Path to the project root directory")],
        max_depth: Annotated[
            int,
            Field(description="Maximum directory depth (default: 3)"),
        ] = 3,
    ) -> str:
        from pypreset.inspect import project_tree

        path = Path(project_dir)
        if not path.is_dir():
            return json.dumps({"error": f"Not a directory: {project_dir}"})

        tree = project_tree(path, max_depth=max_depth)
        return json.dumps({"project": path.name, "tree": tree})

    @mcp.tool(
        name="extract_dependencies",
        description=(
            "Extract all dependencies from a Python project with clean "
            "name and version fields. Supports pyproject.toml (Poetry, "
            "PEP 621, uv/hatch, PDM, flit), requirements*.txt, and Pipfile."
        ),
        tags={"inspect", "dependencies"},
    )
    def extract_dependencies_tool(
        project_dir: Annotated[str, Field(description="Path to the project root directory")],
        group: Annotated[
            str | None,
            Field(description="Filter by group (main, dev, etc.). Returns all if omitted"),
        ] = None,
    ) -> str:
        from pypreset.inspect import extract_dependencies

        path = Path(project_dir)
        if not path.is_dir():
            return json.dumps({"error": f"Not a directory: {project_dir}"})

        deps = extract_dependencies(path)
        if group:
            deps = [d for d in deps if d.group == group]

        return json.dumps(
            {
                "count": len(deps),
                "dependencies": [d.to_dict() for d in deps],
            }
        )

    # ------------------------------------------------------------------
    # generate_badges
    # ------------------------------------------------------------------
    @mcp.tool(
        name="generate_badges",
        description=(
            "Generate badge markdown links for a Python project. "
            "Reads pyproject.toml to detect project name, repository URL, "
            "and license, then returns markdown badge strings."
        ),
        tags={"badges", "readme"},
    )
    def generate_badges_tool(
        project_dir: Annotated[str, Field(description="Path to the project root directory")],
    ) -> str:
        from pypreset.badge_generator import generate_badges
        from pypreset.metadata_utils import read_pyproject_metadata

        path = Path(project_dir)
        if not path.is_dir():
            return json.dumps({"error": f"Not a directory: {project_dir}"})

        meta = read_pyproject_metadata(path)
        badges = generate_badges(
            meta["name"],
            repository_url=meta.get("repository_url"),
            license_id=meta.get("license"),
            has_coverage=False,
            python_version=None,
        )

        return json.dumps(
            {
                "project_name": meta["name"],
                "badge_count": len(badges),
                "badges": [{"label": b.label, "markdown": b.markdown} for b in badges],
            }
        )
