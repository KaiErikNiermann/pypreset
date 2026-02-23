# Contributing

## Prerequisites

- Python >= 3.14
- [Poetry](https://python-poetry.org/docs/#installation)
- [just](https://github.com/casey/just#installation) (command runner)
- [gh](https://cli.github.com/) (only needed for `version` release commands)

## Setup

```bash
git clone <repo-url>
cd pypreset
just install
```

For MCP server development, install with the `mcp` extra:

```bash
poetry install -E mcp
```

## Running Checks

```bash
just all       # Format, lint-fix, typecheck, radon, and test — run this before pushing
just check     # Same but without auto-formatting (lint + typecheck + radon + test)
```

Individual checks:

```bash
just lint        # ruff check src/ tests/
just format      # ruff format src/ tests/
just typecheck   # pyright src/
just radon       # radon cc src/ -a -nd (fails on D-grade or worse)
just test        # pytest -v
just test-cov    # pytest with coverage report
just test-mcp    # MCP server tests only
```

Run a single test file or test:

```bash
poetry run pytest tests/test_models.py -v
poetry run pytest tests/test_models.py::test_function_name -v
```

Integration tests require Docker and [act](https://github.com/nektos/act). They are excluded from the default test run:

```bash
just test-integration       # Non-slow integration tests
just test-integration-full  # All integration tests (requires Docker)
```

## Code Style

- **Formatter/linter**: ruff (line length 100)
- **Type checker**: pyright in strict mode — `# type: ignore` only when truly necessary
- **Complexity**: radon with a threshold of D — functions graded D or worse must be refactored
- Prefer `match`/`case` over `if`/`elif` chains where reasonable
- Use `Literal` string types over plain `str` where values are constrained
- Use `logging` for debug output, not `print`

## Project Structure

```
src/pypreset/
├── cli.py                 # Typer CLI entry point
├── models.py              # Pydantic models and enums
├── preset_loader.py       # YAML preset loading, inheritance, merging
├── generator.py           # Project scaffolding (create)
├── augment_generator.py   # Component generation (augment)
├── project_analyzer.py    # Detect tooling from pyproject.toml
├── template_engine.py     # Jinja2 template rendering
├── interactive_prompts.py # Interactive CLI prompts for augment
├── user_config.py         # User defaults (~/.config/pypreset/)
├── validator.py           # Project structure validation
├── versioning.py          # Release management via git/gh
├── mcp_server/            # MCP server (optional FastMCP dependency)
│   ├── __init__.py        # Server factory and entry point
│   ├── tools.py           # MCP tool handlers
│   ├── resources.py       # MCP resource handlers
│   └── prompts.py         # MCP prompt handlers
├── presets/               # Built-in YAML preset files
└── templates/             # Jinja2 templates (.j2 files)
```

## Adding a New Feature

The typical path for a new feature toggle:

1. **`models.py`** — Add the field to the relevant Pydantic model (and its `Partial*` variant if it participates in preset merging)
2. **`template_engine.py`** — Add the value to the template context dict in `get_template_context()`
3. **`templates/`** — Use the new context variable in the relevant `.j2` template(s)
4. **`preset_loader.py`** — Add override handling in `apply_overrides()` if the feature is CLI-controllable
5. **`cli.py`** — Add the CLI flag to the `create` command
6. **`user_config.py`** — Add as a user-configurable default if appropriate
7. **Tests** — Cover the new behavior

## Adding a New Preset

Create a YAML file in `src/pypreset/presets/`. Presets support single inheritance:

```yaml
name: my-preset
description: A custom project template
base: empty-package  # Optional: inherit from another preset

metadata:
  python_version: "3.12"

dependencies:
  main:
    - requests
  dev:
    - pytest
```

List merging is additive — a child preset's lists extend the parent's rather than replacing them.

## Adding a New Template

1. Create a `.j2` file in `src/pypreset/templates/`
2. Reference it in a preset's `structure.files[].template` field
3. The template receives the context dict from `template_engine.py::get_template_context()`

Templates that differ by package manager come in pairs: `foo.j2` (Poetry) and `foo_uv.j2` (uv).

## MCP Server Development

The MCP server is a thin wrapper around core modules. Tools in `mcp_server/tools.py` call existing functions from `preset_loader`, `generator`, `validator`, etc.

Tests use FastMCP's in-memory `Client` (no STDIO subprocess):

```python
from fastmcp import Client
from pypreset.mcp_server import create_server

async def test_list_presets():
    server = create_server()
    async with Client(server) as client:
        result = await client.call_tool("list_presets", {})
        # ...
```

Run MCP tests: `just test-mcp`

## Config Priority

From lowest to highest:

1. User defaults (`~/.config/pypreset/config.yaml`)
2. Preset config (YAML files with inheritance)
3. CLI flags (`--layout`, `--type-checker`, etc.)
