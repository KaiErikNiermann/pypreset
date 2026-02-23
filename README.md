# pysetup

A meta-tool for scaffolding Python projects with configurable YAML presets. Supports Poetry and uv, generates CI workflows, testing scaffolds, type checking configs, and more.

## Features

- **Preset-based project creation** from YAML configs with single inheritance
- **Augment existing projects** with GitHub Actions workflows, tests, dependabot, `.gitignore`
- **Two package managers**: Poetry and uv (PEP 621 + hatchling)
- **Two layout styles**: `src/` layout and flat layout
- **Type checking**: mypy, ty, or none
- **Code quality**: ruff linting/formatting, radon complexity checks, pre-commit hooks
- **Version management**: bump-my-version integration, GitHub release automation via `gh` CLI
- **User defaults**: persistent config at `~/.config/pysetup/config.yaml`
- **MCP server**: expose all functionality to AI coding assistants via Model Context Protocol

## Installation

```bash
# Core CLI
poetry install

# With MCP server support
poetry install -E mcp
```

## Quick Start

```bash
# Create a CLI tool project with Poetry
pysetup create my-cli --preset cli-tool

# Create a data science project with uv
pysetup create my-analysis --preset data-science --package-manager uv

# Create an empty package with src layout (default)
pysetup create my-package --preset empty-package

# Create a Discord bot
pysetup create my-bot --preset discord-bot
```

## Commands

### `create` — Scaffold a new project

```bash
pysetup create <name> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--preset`, `-p` | Preset to use (default: `empty-package`) |
| `--output`, `-o` | Output directory (default: `.`) |
| `--config`, `-c` | Custom preset YAML file |
| `--package-manager` | `poetry` or `uv` |
| `--layout` | `src` or `flat` |
| `--type-checker` | `mypy`, `ty`, or `none` |
| `--typing` | `none`, `basic`, or `strict` |
| `--python-version` | e.g., `3.12` |
| `--testing` / `--no-testing` | Enable/disable testing scaffold |
| `--formatting` / `--no-formatting` | Enable/disable formatting config |
| `--radon` / `--no-radon` | Enable radon complexity checking |
| `--pre-commit` / `--no-pre-commit` | Generate pre-commit hooks config |
| `--bump-my-version` / `--no-bump-my-version` | Include bump-my-version config |
| `--extra-package`, `-e` | Additional packages (repeatable) |
| `--extra-dev-package`, `-d` | Additional dev packages (repeatable) |
| `--git` / `--no-git` | Initialize git repository |
| `--install` / `--no-install` | Run dependency install after creation |

### `augment` — Add components to an existing project

Analyzes `pyproject.toml` to auto-detect your tooling, then generates the selected components.

```bash
# Interactive mode (prompts for missing values)
pysetup augment ./my-project

# Auto-detect everything, no prompts
pysetup augment --auto

# Generate only specific components
pysetup augment --test-workflow --lint-workflow --gitignore

# Overwrite existing files
pysetup augment --force
```

### `version` — Release management

```bash
pysetup version release <bump>         # Bump, commit, tag, push, release
pysetup version release-version <ver>  # Explicit version, then release
pysetup version rerun <ver>            # Re-tag and push an existing version
pysetup version rerelease <ver>        # Delete and recreate a GitHub release
```

Requires the `gh` CLI to be installed and authenticated.

### Other commands

```bash
pysetup list-presets              # List all available presets
pysetup show-preset <name>        # Show full preset details
pysetup validate [path]           # Validate project structure
pysetup analyze [path]            # Detect and display project tooling
pysetup config show               # Show current user defaults
pysetup config init               # Create default config file
pysetup config set <key> <value>  # Set a config value
```

## Presets

Built-in presets: `empty-package`, `cli-tool`, `data-science`, `discord-bot`.

Presets are YAML files that define metadata, dependencies, directory structure, testing, formatting, and more. They support single inheritance via the `base:` field.

### Custom presets

Place custom preset files in `~/.config/pysetup/presets/` or pass a file directly:

```bash
pysetup create my-project --config ./my-preset.yaml
```

User presets take precedence over built-in presets with the same name.

## User Configuration

Persistent defaults are stored at `~/.config/pysetup/config.yaml` and applied as the lowest-priority layer (presets and CLI flags override them).

```bash
pysetup config init                    # Create with defaults
pysetup config set layout flat         # Set default layout
pysetup config set type_checker ty     # Set default type checker
pysetup config show                    # View current config
```

## MCP Server

An MCP (Model Context Protocol) server exposes pysetup to AI coding assistants over STDIO.

```bash
# Run the server
pysetup-mcp
```

Add to Claude Code `settings.json`:
```json
{
  "mcpServers": {
    "pysetup": {
      "command": "pysetup-mcp",
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
