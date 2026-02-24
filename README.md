<p align="center">
  <img src="https://raw.githubusercontent.com/KaiErikNiermann/pypreset/main/resources/banner.png" alt="PyPreset" height="160">
</p>

<p align="center">
  A meta-tool for scaffolding Python projects with configurable YAML presets.<br>
  Supports Poetry and uv, generates CI workflows, testing scaffolds, type checking configs, and more.
</p>

mcp-name: io.github.KaiErikNiermann/pypreset

## Features

- **Preset-based project creation** from YAML configs with single inheritance
- **Augment existing projects** with CI workflows, tests, Docker, documentation, and more
- **Two package managers**: Poetry and uv (PEP 621 + hatchling)
- **Two layout styles**: `src/` layout and flat layout
- **Type checking**: mypy, pyright, ty, or none
- **Code quality**: ruff linting/formatting, radon complexity checks, pre-commit hooks
- **Docker & devcontainer**: generate multi-stage Dockerfiles, `.dockerignore`, and VS Code devcontainer configs (Docker or Podman)
- **Coverage integration**: Codecov support with configurable thresholds and ignore patterns
- **Documentation scaffolding**: MkDocs (Material theme) or Sphinx (RTD theme) with optional GitHub Pages deployment
- **Multi-environment testing**: tox configuration with tox-uv backend
- **Version management**: bump-my-version integration, GitHub release automation via `gh` CLI
- **Workflow verification**: local GitHub Actions testing with `act` (auto-detect, auto-install, dry-run and full-run modes)
- **PyPI metadata management**: read, set, and check publish-readiness of `pyproject.toml` metadata
- **User defaults**: persistent config at `~/.config/pypreset/config.yaml`
- **MCP server**: expose all functionality to AI coding assistants via the Model Context Protocol

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

# Create with Podman, Codecov, docs, and tox
pypreset create my-project --preset empty-package \
    --container-runtime podman --docker \
    --coverage-tool codecov --coverage-threshold 80 \
    --docs mkdocs --docs-gh-pages \
    --tox
```

## Commands

### `create` -- Scaffold a new project

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
| `--container-runtime` | `docker` or `podman` |
| `--coverage-tool` | `codecov` or `none` |
| `--coverage-threshold` | Minimum coverage % (e.g., `80`) |
| `--docs` | `sphinx`, `mkdocs`, or `none` |
| `--docs-gh-pages` / `--no-docs-gh-pages` | Generate GitHub Pages deploy workflow |
| `--tox` / `--no-tox` | Generate `tox.ini` with tox-uv backend |
| `--git` / `--no-git` | Initialize git repository |
| `--install` / `--no-install` | Run dependency install after creation |
| `--dry-run` | Preview what would be created without generating anything |

### `augment` -- Add components to an existing project

Analyzes `pyproject.toml` to auto-detect your tooling, then generates the selected components. Runs in interactive mode by default (prompts for values it can't detect); use `--auto` to skip prompts.

```bash
pypreset augment [path] [OPTIONS]
```

**Available components:**

| Flag | Component | What it generates |
|------|-----------|-------------------|
| `--test-workflow` / `--no-test-workflow` | Test CI | GitHub Actions workflow that runs pytest across a Python version matrix |
| `--lint-workflow` / `--no-lint-workflow` | Lint CI | GitHub Actions workflow for ruff, type checking, and complexity analysis |
| `--dependabot` / `--no-dependabot` | Dependabot | `.github/dependabot.yml` for automated dependency updates |
| `--tests` / `--no-tests` | Tests directory | `tests/` with template test files and `conftest.py` |
| `--gitignore` / `--no-gitignore` | Gitignore | Python-specific `.gitignore` |
| `--pypi-publish` / `--no-pypi-publish` | PyPI publish | GitHub Actions workflow for OIDC-based publishing to PyPI on release |
| `--dockerfile` / `--no-dockerfile` | Docker | Multi-stage `Dockerfile` and `.dockerignore` (Poetry or uv aware) |
| `--devcontainer` / `--no-devcontainer` | Devcontainer | `.devcontainer/devcontainer.json` with VS Code extensions |
| `--codecov` / `--no-codecov` | Codecov | `codecov.yml` configuration |
| `--docs` | Documentation | Sphinx or MkDocs scaffolding (`--docs sphinx` or `--docs mkdocs`) |
| `--tox` / `--no-tox` | tox | `tox.ini` with tox-uv backend for multi-environment testing |

```bash
# Interactive mode (prompts for missing values)
pypreset augment ./my-project

# Auto-detect everything, no prompts
pypreset augment --auto

# Generate only specific components
pypreset augment --test-workflow --lint-workflow --gitignore

# Add Docker and devcontainer
pypreset augment --dockerfile --devcontainer

# Add PyPI publish workflow
pypreset augment --pypi-publish

# Add documentation scaffolding
pypreset augment --docs mkdocs

# Overwrite existing files
pypreset augment --force
```

### `workflow` -- Local workflow verification

Verify GitHub Actions workflows locally using [act](https://nektosact.com/). The proxy auto-detects whether `act` is installed, can install it on supported systems, and surfaces all `act` output directly.

```bash
# Verify all workflows (dry-run, no containers)
pypreset workflow verify

# Verify a specific workflow file
pypreset workflow verify --workflow .github/workflows/ci.yaml

# Verify a specific job
pypreset workflow verify --job lint

# Full run (executes in containers, requires Docker)
pypreset workflow verify --full-run

# Auto-install act if missing
pypreset workflow verify --auto-install

# Pass extra flags to act
pypreset workflow verify --flag="--secret=GITHUB_TOKEN=xxx"

# Check if act is installed
pypreset workflow check-act

# Install act automatically
pypreset workflow install-act
```

Supported auto-install targets: Arch Linux (pacman), Ubuntu/Debian (apt), Fedora (dnf), macOS/Linux with Homebrew. Other systems get a link to the [act installation page](https://nektosact.com/installation/index.html).

### `version` -- Release management

```bash
pypreset version release --bump patch     # 0.1.0 -> 0.1.1
pypreset version release --bump minor     # 0.1.0 -> 0.2.0
pypreset version release --bump major     # 0.1.0 -> 1.0.0
pypreset version release-version 2.0.0    # Explicit version
pypreset version rerun <ver>              # Re-tag and push an existing version
pypreset version rerelease <ver>          # Delete and recreate a GitHub release
```

Requires the `gh` CLI to be installed and authenticated.

### `metadata` -- PyPI metadata management

```bash
pypreset metadata show                                   # Display current metadata
pypreset metadata set --description "My cool package"    # Set description
pypreset metadata set --github-owner myuser              # Auto-generate URLs
pypreset metadata set --license MIT --keyword python     # Set license and keywords
pypreset metadata check                                  # Check publish-readiness
```

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

**Available tools:**

| Tool | Description |
|------|-------------|
| `create_project` | Create a new project from a preset with optional overrides |
| `augment_project` | Add CI workflows, tests, Docker, docs, and more to an existing project |
| `validate_project` | Check structural correctness of a project directory |
| `verify_workflow` | Verify GitHub Actions workflows locally using act |
| `list_presets` | List all available presets with names and descriptions |
| `show_preset` | Show the full YAML configuration of a specific preset |
| `get_user_config` | Read current user-level defaults |
| `set_user_config` | Update user-level defaults |
| `set_project_metadata` | Set or update PyPI metadata in `pyproject.toml` |

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
