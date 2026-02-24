Quickstart
==========

Installation
------------

Install from PyPI:

.. code-block:: bash

   pip install pypreset

For MCP server support (AI assistant integration):

.. code-block:: bash

   # Install locally
   pip install pypreset[mcp]

   # Or use via uvx (no install needed)
   uvx --from "pypreset[mcp]" pypreset-mcp

The MCP server is also published to the `MCP Registry <https://registry.modelcontextprotocol.io/>`_
as ``io.github.KaiErikNiermann/pypreset``. See :doc:`mcp-server` for client configuration.

For development:

.. code-block:: bash

   git clone https://github.com/KaiErikNiermann/pypreset
   cd pypreset
   poetry install

Creating Your First Project
---------------------------

Create a Python package with sensible defaults:

.. code-block:: bash

   pypreset create my-package

This uses the ``empty-package`` preset by default and generates:

- ``src/my_package/`` with ``__init__.py``
- ``pyproject.toml`` configured for Poetry
- ``tests/`` directory with a template test
- ``.gitignore``
- GitHub Actions CI workflows (test + lint)
- Dependabot configuration
- ``README.md``

Using Presets
-------------

Presets define project templates. List available presets:

.. code-block:: bash

   pypreset list-presets

Create a project with a specific preset:

.. code-block:: bash

   # CLI tool with typer
   pypreset create my-cli --preset cli-tool

   # Data science project with jupyter/pandas/matplotlib
   pypreset create my-analysis --preset data-science

   # Discord bot
   pypreset create my-bot --preset discord-bot

Inspect a preset before using it:

.. code-block:: bash

   pypreset show-preset cli-tool

Preview what a project will look like without creating anything:

.. code-block:: bash

   pypreset create my-project --preset cli-tool --dry-run

Customizing Projects
--------------------

Override preset defaults with CLI flags:

.. code-block:: bash

   # Use uv instead of Poetry
   pypreset create my-project --preset cli-tool --package-manager uv

   # Use flat layout instead of src/
   pypreset create my-project --preset empty-package --layout flat

   # Use ty type checker instead of mypy
   pypreset create my-project --preset cli-tool --type-checker ty

   # Add extra dependencies
   pypreset create my-project --preset empty-package \
       --extra-package requests \
       --extra-dev-package pytest-cov

   # Enable radon complexity checking and pre-commit hooks
   pypreset create my-project --preset cli-tool --radon --pre-commit

   # Generate Dockerfile, .dockerignore, and VS Code devcontainer config
   pypreset create my-service --preset cli-tool --docker --devcontainer

   # Use Podman instead of Docker
   pypreset create my-service --preset cli-tool --docker --container-runtime podman

   # Enable Codecov integration with 80% threshold
   pypreset create my-project --preset empty-package --coverage-tool codecov --coverage-threshold 80

   # Generate MkDocs documentation scaffold with GitHub Pages deployment
   pypreset create my-project --preset empty-package --docs mkdocs --docs-gh-pages

   # Generate Sphinx documentation scaffold
   pypreset create my-project --preset empty-package --docs sphinx

   # Generate tox multi-environment testing config (with tox-uv backend)
   pypreset create my-project --preset empty-package --tox

Augmenting Existing Projects
-----------------------------

Add CI workflows, tests, and configuration to an existing project. The augment
command reads your ``pyproject.toml`` to detect your package manager, test
framework, linter, and type checker, then generates appropriate configurations.

.. code-block:: bash

   # Interactive mode — prompts for missing values
   cd my-existing-project
   pypreset augment

   # Auto-detect everything, no prompts
   pypreset augment --auto

   # Generate only specific components
   pypreset augment --test-workflow --lint-workflow --gitignore

   # Add a PyPI publish workflow
   pypreset augment --pypi-publish

   # Add Dockerfile and devcontainer
   pypreset augment --dockerfile --devcontainer

   # Add Codecov config, documentation, or tox
   pypreset augment --codecov
   pypreset augment --docs mkdocs
   pypreset augment --tox

Available augment components:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Component
     - Description
   * - Test workflow
     - GitHub Actions workflow that runs pytest across a Python version matrix
   * - Lint workflow
     - GitHub Actions workflow for ruff linting, type checking, and complexity analysis
   * - Dependabot
     - ``.github/dependabot.yml`` for automated dependency updates (pip and GitHub Actions)
   * - Tests directory
     - ``tests/`` directory with template test files and ``conftest.py``
   * - Gitignore
     - Python-specific ``.gitignore`` covering common build artifacts, caches, and IDE files
   * - PyPI publish
     - GitHub Actions workflow for OIDC-based publishing to PyPI on release events
   * - Dockerfile
     - Multi-stage ``Dockerfile`` and ``.dockerignore`` (Poetry or uv aware, src or flat layout)
   * - Devcontainer
     - ``.devcontainer/devcontainer.json`` with VS Code extensions for the detected tooling
   * - Codecov
     - ``codecov.yml`` configuration for coverage reporting
   * - Documentation
     - Sphinx (RTD theme) or MkDocs (Material theme) scaffolding with optional GitHub Pages deploy
   * - tox
     - ``tox.ini`` with tox-uv backend for testing across multiple Python versions

Verifying Workflows
-------------------

Verify that generated GitHub Actions workflows are valid using
`act <https://nektosact.com/>`_ (a local GitHub Actions runner):

.. code-block:: bash

   # Dry-run verification (no containers)
   pypreset workflow verify

   # Verify a specific workflow and job
   pypreset workflow verify --workflow .github/workflows/ci.yaml --job lint

   # Full execution in containers (requires Docker)
   pypreset workflow verify --full-run

   # Auto-install act if it's not on the system
   pypreset workflow verify --auto-install

   # Check if act is available
   pypreset workflow check-act

   # Install act
   pypreset workflow install-act

.. note::

   Some workflows cannot be tested locally (e.g. those that depend on GitHub-specific
   secrets or deployment contexts). The tool surfaces all ``act`` errors directly
   for you to interpret.

User Configuration
------------------

Set persistent defaults so you don't repeat flags:

.. code-block:: bash

   # Create default config
   pypreset config init

   # Set defaults
   pypreset config set layout flat
   pypreset config set type_checker ty
   pypreset config set package_manager uv
   pypreset config set container_runtime podman
   pypreset config set documentation_tool mkdocs

   # View current config
   pypreset config show

Config is stored at ``~/.config/pypreset/config.yaml``. Presets and CLI flags
override these defaults.

Version Management
------------------

Bump, tag, and release:

.. code-block:: bash

   pypreset version release --bump patch       # 0.1.0 -> 0.1.1
   pypreset version release --bump minor       # 0.1.0 -> 0.2.0
   pypreset version release --bump major       # 0.1.0 -> 1.0.0
   pypreset version release-version 2.0.0      # Explicit version

Requires the ``gh`` CLI to be installed and authenticated.

PyPI Metadata
-------------

Manage ``pyproject.toml`` metadata for publishing:

.. code-block:: bash

   # Show current metadata
   pypreset metadata show

   # Set fields
   pypreset metadata set --description "My cool package"
   pypreset metadata set --github-owner myuser    # auto-generates URLs
   pypreset metadata set --license MIT --keyword python --keyword cli

   # Check if ready for publishing
   pypreset metadata check
