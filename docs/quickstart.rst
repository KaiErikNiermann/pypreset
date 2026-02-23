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
- GitHub Actions CI workflows
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

Augmenting Existing Projects
-----------------------------

Add CI workflows, tests, and configuration to an existing project:

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

The augment command reads your ``pyproject.toml`` to detect your package manager,
test framework, linter, and type checker, then generates appropriate configurations.

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

   # View current config
   pypreset config show

Config is stored at ``~/.config/pypreset/config.yaml``. Presets and CLI flags
override these defaults.

Version Management
------------------

Bump, tag, and release:

.. code-block:: bash

   pypreset version release patch       # 0.1.0 → 0.1.1
   pypreset version release minor       # 0.1.0 → 0.2.0
   pypreset version release major       # 0.1.0 → 1.0.0
   pypreset version release-version 2.0.0  # Explicit version

Requires the ``gh`` CLI to be installed and authenticated.
