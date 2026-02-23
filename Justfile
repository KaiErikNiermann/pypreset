set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# List recipes
default:
    @just --list

# Install dependencies
install:
    poetry install

# Run tests
test:
    poetry run pytest -v

# Run tests with coverage
test-cov:
    poetry run pytest -v --cov=pypreset --cov-report=term-missing

# Run integration tests (requires poetry)
test-integration:
    poetry run pytest tests/test_integration.py -v -m "not slow"

# Run full integration tests including slow act tests (requires docker)
test-integration-full:
    poetry run pytest tests/test_integration.py -v

# Run linting
lint:
    poetry run ruff check src/ tests/

# Fix linting issues
lint-fix:
    poetry run ruff check --fix src/ tests/

# Format code
format:
    poetry run ruff format src/ tests/

# Run type checking
typecheck:
    poetry run pyright src/

# Run cyclomatic complexity check (fail on D or worse)
radon:
    poetry run radon cc src/ -a -nd

# Run all checks
check: lint typecheck radon test

# Clean up
clean:
    rm -rf .pytest_cache
    rm -rf .mypy_cache
    rm -rf .ruff_cache
    rm -rf .coverage
    rm -rf htmlcov
    rm -rf docs/_build
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name '*.pyc' -delete

# Development setup
dev: install
    @echo "Development environment ready!"

# Run the CLI
run:
    poetry run pypreset

# Run the MCP server (STDIO transport)
mcp-serve:
    poetry run pypreset-mcp

# Run MCP server tests only
test-mcp:
    poetry run pytest tests/test_mcp_server/ -v

# Build package
build:
    poetry build

# Generate JSON schema from Pydantic models for YAML validation
schema:
    poetry run python scripts/generate_schema.py

# Build docs locally
docs:
    poetry run sphinx-build -b html docs docs/_build/html

# Serve docs locally (build + open)
docs-serve: docs
    python -m http.server 8000 -d docs/_build/html

# --- Versioning ---

# Bump version, commit, tag, push, and create GitHub release
release bump="patch":
    @bump="{{bump}}"; \
        if [[ "$bump" == bump=* ]]; then bump="${bump#bump=}"; fi; \
        poetry version "$bump"
    @version=$(poetry version --short); \
        just _release "$version"

# Use an explicit version, then commit, tag, push, and release
release-version version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        poetry version "$version"; \
        just _release "$version"

# Re-trigger publish for an existing version by re-tagging HEAD
rerun version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        git push; \
        git tag -d v"$version" || true; \
        git push --delete origin v"$version" || true; \
        git tag v"$version"; \
        git push origin v"$version"

# Delete and recreate the GitHub release + retag HEAD at the same version
rerelease version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        gh release delete v"$version" -y || true; \
        just rerun "$version"; \
        gh release create v"$version" --title "v$version" --generate-notes

# Internal helper — commit, tag, push, create release
_release version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        git add pyproject.toml; \
        git add -f poetry.lock; \
        git commit -m "chore(release): v$version"; \
        git push; \
        git tag v"$version"; \
        git push origin v"$version"; \
        gh release create v"$version" --title "v$version" --generate-notes

all: format lint-fix typecheck radon test
