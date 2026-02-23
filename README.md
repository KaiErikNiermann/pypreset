# pypreset

mcp-name: io.github.KaiErikNiermann/pypreset

A meta-tool for scaffolding Python projects with configurable YAML presets. Supports Poetry and uv, generates CI workflows, testing scaffolds, type checking configs, and more.

## Features

- **Preset-based project creation** from YAML configs with single inheritance
- **Augment existing projects** with GitHub Actions workflows, tests, dependabot, `.gitignore`
- **Two package managers**: Poetry and uv (PEP 621 + hatchling)
- **Two layout styles**: `src/` layout and flat layout
- **Type checking**: mypy, pyright, ty, or none
- **Code quality**: ruff linting/formatting, radon complexity checks, pre-commit hooks
- **Docker & devcontainer**: generate multi-stage Dockerfiles, `.dockerignore`, and VS Code devcontainer configs
- **Version management**: bump-my-version integration, GitHub release automation via `gh` CLI
- **User defaults**: persistent config at `~/.config/pypreset/config.yaml`
- **MCP server**: expose all functionality to AI coding assistants via Model Context Protocol

## Installation

```bash
pip install pypreset

# With MCP server support
pip install pypreset[mcp]
```

## Quick Start

```bash
# Create a CLI tool project with Poetry
pypreset create my-cli --preset cli-tool

# Create a data science project with uv
pypreset create my-analysis --preset data-science --package-manager uv

# Create an empty package with src layout (default)
pypreset create my-package --preset empty-package

# Create a Discord bot
pypreset create my-bot --preset discord-bot

# Create a project with Docker support
pypreset create my-service --preset cli-tool --docker --devcontainer
```

## Commands

### `create` — Scaffold a new project

```bash
pypreset create <name> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--preset`, `-p` | Preset to use (default: `empty-package`) |
| `--output`, `-o` | Output directory (default: `.`) |
| `--config`, `-c` | Custom preset YAML file |
| `--package-manager` | `poetry` or `uv` |
| `--layout` | `src` or `flat` |
| `--type-checker` | `mypy`, `pyright`, `ty`, or `none` |
| `--typing` | `none`, `basic`, or `strict` |
| `--python-version` | e.g., `3.12` |
| `--testing` / `--no-testing` | Enable/disable testing scaffold |
| `--formatting` / `--no-formatting` | Enable/disable formatting config |
| `--radon` / `--no-radon` | Enable radon complexity checking |
| `--pre-commit` / `--no-pre-commit` | Generate pre-commit hooks config |
| `--bump-my-version` / `--no-bump-my-version` | Include bump-my-version config |
| `--extra-package`, `-e` | Additional packages (repeatable) |
| `--extra-dev-package`, `-d` | Additional dev packages (repeatable) |
| `--docker` / `--no-docker` | Generate Dockerfile and `.dockerignore` |
| `--devcontainer` / `--no-devcontainer` | Generate `.devcontainer/` configuration |
| `--git` / `--no-git` | Initialize git repository |
| `--install` / `--no-install` | Run dependency install after creation |

### `augment` — Add components to an existing project

Analyzes `pyproject.toml` to auto-detect your tooling, then generates the selected components.

```bash
# Interactive mode (prompts for missing values)
pypreset augment ./my-project

# Auto-detect everything, no prompts
pypreset augment --auto

# Generate only specific components
pypreset augment --test-workflow --lint-workflow --gitignore

# Add Dockerfile and devcontainer config
pypreset augment --dockerfile --devcontainer

# Overwrite existing files
pypreset augment --force
```

### `version` — Release management

```bash
pypreset version release <bump>         # Bump, commit, tag, push, release
pypreset version release-version <ver>  # Explicit version, then release
pypreset version rerun <ver>            # Re-tag and push an existing version
pypreset version rerelease <ver>        # Delete and recreate a GitHub release
```

Requires the `gh` CLI to be installed and authenticated.

### Other commands

```bash
pypreset list-presets              # List all available presets
pypreset show-preset <name>        # Show full preset details
pypreset validate [path]           # Validate project structure
pypreset analyze [path]            # Detect and display project tooling
pypreset config show               # Show current user defaults
pypreset config init               # Create default config file
pypreset config set <key> <value>  # Set a config value
```

## Presets

Built-in presets: `empty-package`, `cli-tool`, `data-science`, `discord-bot`.

Presets are YAML files that define metadata, dependencies, directory structure, testing, formatting, and more. They support single inheritance via the `base:` field.

### Custom presets

Place custom preset files in `~/.config/pypreset/presets/` or pass a file directly:

```bash
pypreset create my-project --config ./my-preset.yaml
```

User presets take precedence over built-in presets with the same name.

## User Configuration

Persistent defaults are stored at `~/.config/pypreset/config.yaml` and applied as the lowest-priority layer (presets and CLI flags override them).

```bash
pypreset config init                    # Create with defaults
pypreset config set layout flat         # Set default layout
pypreset config set type_checker ty     # Set default type checker
pypreset config show                    # View current config
```

## MCP Server

pypreset is published to the [MCP Registry](https://registry.modelcontextprotocol.io/) as `io.github.KaiErikNiermann/pypreset`.

**Install via the registry (recommended):**

```bash
# Claude Code
claude mcp add pypreset -- uvx --from "pypreset[mcp]" pypreset-mcp

# Or add manually to ~/.claude/settings.json
```

```json
{
  "mcpServers": {
    "pypreset": {
      "command": "uvx",
      "args": ["--from", "pypreset[mcp]", "pypreset-mcp"]
    }
  }
}
```

**Or install locally:**

```bash
pip install pypreset[mcp]
```

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

**Available tools**: `create_project`, `augment_project`, `validate_project`, `list_presets`, `show_preset`, `get_user_config`, `set_user_config`

**Resources**: `preset://list`, `config://user`, `template://list`

**Prompts**: `create-project`, `augment-project`

## Development

All tasks use the `Justfile`:

```bash
just install     # Install dependencies
just test        # Run tests
just test-cov    # Tests with coverage
just lint        # Ruff check
just format      # Ruff format
just typecheck   # Pyright
just radon       # Cyclomatic complexity check
just check       # lint + typecheck + radon + test
just all         # format + lint-fix + typecheck + radon + test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT
