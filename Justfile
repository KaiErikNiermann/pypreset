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

# Bump version, commit, tag, push, create GitHub release, wait for PyPI, publish MCP
release bump="patch":
    @bump="{{bump}}"; \
        if [[ "$bump" == bump=* ]]; then bump="${bump#bump=}"; fi; \
        poetry version "$bump"
    @version=$(poetry version --short); \
        just _release "$version"

# Use an explicit version, then full release pipeline
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
        git push origin v"$version"; \
        just _wait-pypi "$version"; \
        just _publish-mcp "$version"

# Delete and recreate the GitHub release + retag HEAD at the same version
rerelease version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        gh release delete v"$version" -y || true; \
        just rerun "$version"; \
        gh release create v"$version" --title "v$version" --generate-notes

# Internal: sync versions, commit, tag, push, create release, wait for PyPI, publish MCP
_release version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        just _sync-versions "$version"; \
        poetry lock; \
        git add pyproject.toml server.json; \
        git add -f poetry.lock; \
        git commit -m "chore(release): v$version"; \
        git push; \
        git tag v"$version"; \
        git push origin v"$version"; \
        gh release create v"$version" --title "v$version" --generate-notes; \
        just _wait-pypi "$version"; \
        just _publish-mcp "$version"

# Internal: update version in server.json to match pyproject.toml
_sync-versions version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$version\"/g" server.json; \
        echo "Synced server.json to v$version"

# Internal: wait for PyPI publish workflow to complete
_wait-pypi version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        echo "Waiting for PyPI publish workflow..."; \
        run_id=$(gh run list --workflow "Publish to PyPI" --limit 1 --json databaseId -q '.[0].databaseId'); \
        gh run watch "$run_id" --exit-status && \
        echo "PyPI publish succeeded for v$version" || \
        { echo "PyPI publish failed — skipping MCP registry publish"; exit 1; }

# Internal: publish to MCP registry (auto-login on 401, wait for PyPI propagation on 404)
_publish-mcp version:
    @version="{{version}}"; \
        if [[ "$version" == version=* ]]; then version="${version#version=}"; fi; \
        echo "Publishing to MCP registry..."; \
        attempt=1; max_attempts=12; \
        while [ "$attempt" -le "$max_attempts" ]; do \
            output=$(mcp-publisher publish 2>&1) && \
            { echo "MCP registry publish succeeded for v$version"; break; } || true; \
            if echo "$output" | grep -q "401\|expired\|Unauthorized"; then \
                echo "Token expired — re-authenticating..."; \
                mcp-publisher login github; \
                echo "Retrying publish..."; \
            elif echo "$output" | grep -q "404\|not found\|Not Found"; then \
                echo "PyPI package not yet visible (attempt $attempt/$max_attempts) — waiting 15s..."; \
                sleep 15; \
            else \
                echo "MCP registry publish failed: $output"; exit 1; \
            fi; \
            attempt=$((attempt + 1)); \
        done; \
        if [ "$attempt" -gt "$max_attempts" ]; then \
            echo "MCP registry publish failed after $max_attempts attempts"; exit 1; \
        fi

all: format lint-fix typecheck radon test
