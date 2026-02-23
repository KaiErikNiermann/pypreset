"""Tests for validating generated GitHub Actions workflow YAML.

These tests render workflow templates for various configurations and validate
that the resulting YAML is structurally correct without requiring Docker or act.
"""

import yaml

from pysetup.template_engine import create_jinja_environment, render_template


def _make_context(
    *,
    testing_enabled: bool = True,
    testing_framework: str = "pytest",
    coverage: bool = False,
    formatting_enabled: bool = True,
    formatting_tool: str = "ruff",
    typing_level: str = "strict",
    type_checker: str = "mypy",
    radon: bool = False,
    python_version: str = "3.11",
    package_name: str = "test_project",
) -> dict:
    return {
        "project": {
            "name": "test-project",
            "package_name": package_name,
            "version": "0.1.0",
            "description": "Test project",
            "authors": [],
            "license": None,
            "readme": "README.md",
            "python_version": python_version,
            "keywords": [],
            "classifiers": [],
        },
        "dependencies": {"main": [], "dev": [], "optional": {}},
        "testing": {
            "enabled": testing_enabled,
            "framework": testing_framework,
            "coverage": coverage,
        },
        "formatting": {
            "enabled": formatting_enabled,
            "tool": formatting_tool,
            "line_length": 100,
            "radon": radon,
            "pre_commit": False,
            "version_bumping": False,
            "type_checker": type_checker,
        },
        "dependabot": {
            "enabled": True,
            "schedule": "weekly",
            "open_pull_requests_limit": 5,
        },
        "typing_level": typing_level,
        "layout": "src",
        "package_manager": "poetry",
        "entry_points": [],
        "extras": {},
    }


def _render_workflow(template_name: str, context: dict) -> dict:
    """Render a workflow template and parse the resulting YAML."""
    env = create_jinja_environment()
    content = render_template(env, template_name, context)
    return yaml.safe_load(content)


class TestPoetryWorkflowStructure:
    """Validate structure of Poetry CI workflow."""

    def test_valid_yaml(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        assert isinstance(workflow, dict)
        assert "name" in workflow
        # YAML parses bare `on:` as boolean True
        assert True in workflow or "on" in workflow
        assert "jobs" in workflow

    def test_has_test_job_when_testing_enabled(self) -> None:
        ctx = _make_context(testing_enabled=True)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        assert "test" in workflow["jobs"]

    def test_no_test_job_when_testing_disabled(self) -> None:
        ctx = _make_context(testing_enabled=False)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        assert "test" not in workflow["jobs"]

    def test_has_lint_job_when_formatting_enabled(self) -> None:
        ctx = _make_context(formatting_enabled=True)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        assert "lint" in workflow["jobs"]

    def test_no_lint_job_when_formatting_disabled(self) -> None:
        ctx = _make_context(formatting_enabled=False, testing_enabled=True)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        assert "lint" not in workflow["jobs"]

    def test_test_job_has_matrix(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        test_job = workflow["jobs"]["test"]
        assert "strategy" in test_job
        assert "matrix" in test_job["strategy"]
        assert "python-version" in test_job["strategy"]["matrix"]

    def test_lint_job_has_checkout_step(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        uses_values = [s.get("uses", "") for s in lint_steps]
        assert any("checkout" in u for u in uses_values)

    def test_mypy_step_present_for_strict_typing(self) -> None:
        ctx = _make_context(typing_level="strict", type_checker="mypy")
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        step_names = [s.get("name", "") for s in lint_steps]
        assert any("mypy" in n.lower() for n in step_names)

    def test_ty_step_present_for_ty_checker(self) -> None:
        ctx = _make_context(typing_level="strict", type_checker="ty")
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        step_names = [s.get("name", "") for s in lint_steps]
        assert any("ty" in n.lower() for n in step_names)

    def test_no_type_check_step_when_typing_none(self) -> None:
        ctx = _make_context(typing_level="none")
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        step_names = [s.get("name", "") for s in lint_steps]
        assert not any("mypy" in n.lower() or "type check" in n.lower() for n in step_names)

    def test_radon_step_when_enabled(self) -> None:
        ctx = _make_context(radon=True)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        step_names = [s.get("name", "") for s in lint_steps]
        assert any("radon" in n.lower() for n in step_names)

    def test_coverage_step_when_enabled(self) -> None:
        ctx = _make_context(coverage=True)
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        step_names = [s.get("name", "") for s in test_steps]
        assert any("coverage" in n.lower() for n in step_names)

    def test_poetry_install_step_present(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        uses_values = [s.get("uses", "") for s in test_steps]
        assert any("install-poetry" in u for u in uses_values)


class TestUvWorkflowStructure:
    """Validate structure of uv CI workflow."""

    def test_valid_yaml(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        assert isinstance(workflow, dict)
        assert "jobs" in workflow

    def test_uses_setup_uv_action(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        uses_values = [s.get("uses", "") for s in test_steps]
        assert any("setup-uv" in u for u in uses_values)

    def test_uses_uv_sync(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        run_cmds = [s.get("run", "") for s in test_steps]
        assert any("uv sync" in r for r in run_cmds)

    def test_uses_uv_run_pytest(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        run_cmds = [s.get("run", "") for s in test_steps]
        assert any("uv run pytest" in r for r in run_cmds)

    def test_no_poetry_references(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        test_steps = workflow["jobs"]["test"]["steps"]
        for step in test_steps:
            step_str = str(step)
            assert "poetry" not in step_str.lower()

    def test_ty_step_in_uv_workflow(self) -> None:
        ctx = _make_context(typing_level="strict", type_checker="ty")
        workflow = _render_workflow("github_ci_uv.yaml.j2", ctx)
        lint_steps = workflow["jobs"]["lint"]["steps"]
        run_cmds = [s.get("run", "") for s in lint_steps]
        assert any("uv run ty check" in r for r in run_cmds)


class TestDependabotConfig:
    """Validate generated dependabot.yml."""

    def test_valid_yaml(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("dependabot.yml.j2", ctx)
        assert isinstance(workflow, dict)
        assert "version" in workflow
        assert workflow["version"] == 2
        assert "updates" in workflow

    def test_has_pip_ecosystem(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("dependabot.yml.j2", ctx)
        ecosystems = [u["package-ecosystem"] for u in workflow["updates"]]
        assert "pip" in ecosystems

    def test_has_github_actions_ecosystem(self) -> None:
        ctx = _make_context()
        workflow = _render_workflow("dependabot.yml.j2", ctx)
        ecosystems = [u["package-ecosystem"] for u in workflow["updates"]]
        assert "github-actions" in ecosystems
