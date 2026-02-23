Quickstart
==========

Installation
------------

Install from PyPI:

.. code-block:: bash

   pip install pysetup

For MCP server support (AI assistant integration):

.. code-block:: bash

   pip install pysetup[mcp]

For development:

.. code-block:: bash

   git clone https://github.com/OWNER/pysetup
   cd pysetup
   poetry install

Creating Your First Project
---------------------------

Create a Python package with sensible defaults:

.. code-block:: bash

   pysetup create my-package

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

   pysetup list-presets

Create a project with a specific preset:

.. code-block:: bash

   # CLI tool with typer
   pysetup create my-cli --preset cli-tool

   # Data science project with jupyter/pandas/matplotlib
   pysetup create my-analysis --preset data-science

   # Discord bot
   pysetup create my-bot --preset discord-bot

Inspect a preset before using it:

.. code-block:: bash

   pysetup show-preset cli-tool

Customizing Projects
--------------------

Override preset defaults with CLI flags:

.. code-block:: bash

   # Use uv instead of Poetry
   pysetup create my-project --preset cli-tool --package-manager uv

   # Use flat layout instead of src/
   pysetup create my-project --preset empty-package --layout flat

   # Use ty type checker instead of mypy
   pysetup create my-project --preset cli-tool --type-checker ty

   # Add extra dependencies
   pysetup create my-project --preset empty-package \
       --extra-package requests \
       --extra-dev-package pytest-cov

   # Enable radon complexity checking and pre-commit hooks
   pysetup create my-project --preset cli-tool --radon --pre-commit

Augmenting Existing Projects
-----------------------------

Add CI workflows, tests, and configuration to an existing project:

.. code-block:: bash

   # Interactive mode — prompts for missing values
   cd my-existing-project
   pysetup augment

   # Auto-detect everything, no prompts
   pysetup augment --auto

   # Generate only specific components
   pysetup augment --test-workflow --lint-workflow --gitignore

   # Add a PyPI publish workflow
   pysetup augment --pypi-publish

The augment command reads your ``pyproject.toml`` to detect your package manager,
test framework, linter, and type checker, then generates appropriate configurations.

User Configuration
------------------

Set persistent defaults so you don't repeat flags:

.. code-block:: bash

   # Create default config
   pysetup config init

   # Set defaults
   pysetup config set layout flat
   pysetup config set type_checker ty
   pysetup config set package_manager uv

   # View current config
   pysetup config show

Config is stored at ``~/.config/pysetup/config.yaml``. Presets and CLI flags
override these defaults.

Version Management
------------------

Bump, tag, and release:

.. code-block:: bash

   pysetup version release patch       # 0.1.0 → 0.1.1
   pysetup version release minor       # 0.1.0 → 0.2.0
   pysetup version release major       # 0.1.0 → 1.0.0
   pysetup version release-version 2.0.0  # Explicit version

Requires the ``gh`` CLI to be installed and authenticated.
