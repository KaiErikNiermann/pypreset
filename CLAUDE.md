# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All common tasks are defined in the `Justfile` (use `just <target>`):

```bash
just install        # poetry install
just test           # pytest -v
just test-cov       # pytest with coverage report
just test-mcp       # pytest tests/test_mcp_server/ -v
just lint           # ruff check src/ tests/
just lint-fix       # ruff check --fix src/ tests/
just format         # ruff format src/ tests/
just typecheck      # pyright src/
just radon          # cyclomatic complexity check (fail on D+)
just check          # lint + typecheck + radon + test
just schema         # regenerate JSON schemas from Pydantic models
just mcp-serve      # run the MCP server (STDIO transport)
just all            # format + lint-fix + typecheck + radon + test
```

Run a single test file:
```bash
poetry run pytest tests/test_models.py -v
```

Run a specific test:
```bash
poetry run pytest tests/test_models.py::test_name -v
```

## Architecture

`pypreset` is a CLI meta-tool that scaffolds Poetry-based Python projects from YAML presets. The data flow is:

**`create` command flow:**
1. `cli.py` — Typer entry point; parses args into `OverrideOptions`
2. `preset_loader.py` → `build_project_config()` — loads a YAML preset, resolves its inheritance chain (`base:` field), deep-merges configs, applies runtime overrides, replaces `__PROJECT_NAME__`/`__PACKAGE_NAME__` placeholders, returns a `ProjectConfig`
3. `generator.py` → `ProjectGenerator` — writes directories, renders Jinja2 templates from `src/pypreset/templates/`, creates `pyproject.toml`, README, `.gitignore`, GitHub workflows, and optionally runs `git init` / `poetry install`
4. `validator.py` — checks the generated project for structural correctness

**`augment` command flow** (adds CI/tests/gitignore to an *existing* project):
1. `project_analyzer.py` → `analyze_project()` — reads `pyproject.toml` to detect package manager, linter, test framework, type checker
2. `interactive_prompts.py` — fills in any values the analyzer couldn't detect
3. `augment_generator.py` → `augment_project()` — renders and writes only the selected components, skipping existing files unless `--force`

**`version` subcommands** (`release`, `release-version`, `rerun`, `rerelease`):
- Delegated to `versioning.py` → `VersioningAssistant` — bumps version in `pyproject.toml`, commits, tags, pushes, creates GitHub releases via `gh` CLI.

### Key modules

| File | Purpose |
|------|---------|
| `models.py` | All Pydantic models: `ProjectConfig`, `PresetConfig`, `OverrideOptions`, enums (`LayoutStyle`, `TypeChecker`, `CreationPackageManager`, etc.), and `Partial*` variants for preset merging |
| `preset_loader.py` | YAML loading, preset inheritance (`deep_merge`), placeholder substitution |
| `template_engine.py` | Jinja2 environment setup; `get_template_context()` builds the dict available in all `.j2` templates |
| `generator.py` | `ProjectGenerator` class; selects templates based on `package_manager` (Poetry vs uv) |
| `augment_generator.py` | Generates individual components into existing projects |
| `project_analyzer.py` | Heuristic detection of tooling from `pyproject.toml` |
| `user_config.py` | User-level defaults from `~/.config/pypreset/config.yaml`; applied as lowest-priority base layer |
| `versioning.py` | `VersioningAssistant`; wraps `poetry version`, git, and `gh` CLI |
| `mcp_server/` | MCP server subpackage — tools, resources, and prompts for AI assistant integration |

### Preset system

- Built-in presets live in `src/pypreset/presets/*.yaml`
- User presets can be placed in `~/.config/pypreset/presets/`
- Presets support single inheritance via `base: <preset-name>`
- List merging in `deep_merge` is **additive** (child list extends parent list, not replaces)
- `__PROJECT_NAME__` and `__PACKAGE_NAME__` are placeholder strings replaced in entry points

### Templates

Jinja2 templates in `src/pypreset/templates/` receive a `project` context dict (built in `template_engine.py::get_template_context()`). Template names referenced in preset YAML `files[].template` fields must match filenames in this directory.

Key templates come in pairs for Poetry vs uv:
- `pyproject.toml.j2` (Poetry) / `pyproject_uv.toml.j2` (uv with PEP 621 `[project]` + hatchling)
- `github_ci.yaml.j2` (Poetry) / `github_ci_uv.yaml.j2` (uv with `astral-sh/setup-uv`)

### Config priority (lowest to highest)

1. User defaults (`~/.config/pypreset/config.yaml`) via `apply_user_defaults()`
2. Preset config (YAML preset files with inheritance)
3. CLI overrides (`--layout`, `--type-checker`, `--package-manager`, etc.)

### MCP server (`src/pypreset/mcp_server/`)

An MCP (Model Context Protocol) server that exposes pypreset functionality to AI coding assistants via STDIO transport. Install with `pip install pypreset[mcp]` or `poetry install -E mcp`.

**Tools** (`tools.py`): `create_project`, `augment_project`, `validate_project`, `list_presets`, `show_preset`, `get_user_config`, `set_user_config`

**Resources** (`resources.py`): `preset://list`, `config://user`, `template://list`

**Prompts** (`prompts.py`): `create-project` (guided project creation), `augment-project` (guided augmentation)

Built with FastMCP 3.x. Tests use `fastmcp.Client` for in-memory testing (no STDIO subprocess needed). The MCP server is a thin wrapper — all tools delegate to existing core modules.

Claude Code `settings.json` example:
```json
{
  "mcpServers": {
    "pypreset": {
      "command": "pypreset-mcp",
      "args": []
    }
  }
}
```

## Python conventions (from `.github/instructions/`)

- Use `match`/`case` over `if`/`elif` chains where reasonable
- Strict typing everywhere; append `# type: ignore` only when truly necessary
- Use `Literal` string types over plain `str` where values are constrained
- CLI tools use **typer**, not argparse
- Type checking uses **pyright** only (not mypy, despite mypy being in dev deps)
- Use proper `logging` for debug output; disable it in normal runs
