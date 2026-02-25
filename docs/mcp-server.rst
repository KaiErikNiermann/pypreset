MCP Server
==========

pypreset includes an `MCP <https://modelcontextprotocol.io/>`_ (Model Context Protocol)
server that lets AI coding assistants create projects, augment existing ones,
verify workflows, manage metadata, and configure defaults — all programmatically.

Installation
------------

pypreset is published to the `MCP Registry <https://registry.modelcontextprotocol.io/>`_
as ``io.github.KaiErikNiermann/pypreset``.

**Install from the registry via uvx (recommended):**

.. code-block:: bash

   # Claude Code — one-liner
   claude mcp add pypreset -- uvx --from "pypreset[mcp]" pypreset-mcp

No local install needed — ``uvx`` fetches the package on demand.

**Or install locally from PyPI:**

.. code-block:: bash

   pip install pypreset[mcp]

Client Configuration
--------------------

**Claude Code** (``~/.claude/settings.json``):

Using ``uvx`` (no local install):

.. code-block:: json

   {
     "mcpServers": {
       "pypreset": {
         "command": "uvx",
         "args": ["--from", "pypreset[mcp]", "pypreset-mcp"]
       }
     }
   }

Using a local install:

.. code-block:: json

   {
     "mcpServers": {
       "pypreset": {
         "command": "pypreset-mcp",
         "args": []
       }
     }
   }

**Claude Desktop** (``claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "pypreset": {
         "command": "uvx",
         "args": ["--from", "pypreset[mcp]", "pypreset-mcp"]
       }
     }
   }

Available Tools
---------------

Tools are actions the AI assistant can invoke:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Tool
     - Description
   * - ``create_project``
     - Create a new project from a preset with optional overrides (layout, type checker,
       package manager, typing level, Python version, Docker, devcontainer, docs, coverage, tox)
   * - ``augment_project``
     - Add CI workflows, tests, gitignore, dependabot, Dockerfile, devcontainer, codecov,
       documentation, tox, and PyPI publish workflow to an existing project.
       Auto-detects tooling from ``pyproject.toml``
   * - ``validate_project``
     - Check structural correctness of a generated project directory
   * - ``verify_workflow``
     - Verify GitHub Actions workflows locally using ``act``. Checks if act is installed
       (warns if not), optionally auto-installs on supported Linux distros, then runs
       workflows in dry-run or full mode. All act output is surfaced directly. Accepts
       workflow file, job filter, event type, platform mapping, and extra flags
   * - ``list_presets``
     - List all available presets with names and descriptions
   * - ``show_preset``
     - Show the full YAML configuration of a specific preset
   * - ``get_user_config``
     - Read current user-level defaults from ``~/.config/pypreset/config.yaml``
   * - ``set_user_config``
     - Update user-level defaults (merges into existing config)
   * - ``set_project_metadata``
     - Set or update PyPI metadata (description, authors, license, URLs, keywords) in
       ``pyproject.toml``. Supports auto-generating URLs from a ``github_owner`` parameter.
       Returns publish-readiness warnings for empty or placeholder fields
   * - ``migrate_to_uv``
     - Migrate a Python project to uv from another package manager (Poetry, Pipenv,
       pip-tools, or pip) using the upstream
       `migrate-to-uv <https://github.com/mkniewallner/migrate-to-uv>`_ tool.
       Requires ``migrate-to-uv`` to be installed. Supports dry-run, custom build
       backends, dependency group strategies, and all upstream flags

Tool Parameters
~~~~~~~~~~~~~~~

**verify_workflow** accepts these parameters:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``project_dir``
     - (required)
     - Path to the project root directory
   * - ``workflow_file``
     - ``null``
     - Specific workflow file relative to project (e.g. ``.github/workflows/ci.yaml``)
   * - ``job``
     - ``null``
     - Specific job name to verify; runs all jobs if omitted
   * - ``event``
     - ``"push"``
     - GitHub event to simulate
   * - ``dry_run``
     - ``true``
     - Validate without executing containers
   * - ``platform_map``
     - ``null``
     - Platform mapping (e.g. ``ubuntu-latest=catthehacker/ubuntu:act-latest``)
   * - ``extra_flags``
     - ``null``
     - Additional flags to pass through to act
   * - ``timeout``
     - ``600``
     - Timeout in seconds for act commands
   * - ``auto_install``
     - ``false``
     - Attempt to auto-install act if not found

**set_project_metadata** accepts these parameters:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``project_dir``
     - (required)
     - Path to the project directory
   * - ``description``
     - ``null``
     - Short package description for PyPI
   * - ``authors``
     - ``null``
     - Authors list, e.g. ``["Name <email@example.com>"]``
   * - ``license``
     - ``null``
     - SPDX license identifier (e.g. ``MIT``, ``Apache-2.0``)
   * - ``keywords``
     - ``null``
     - PyPI search keywords
   * - ``classifiers``
     - ``null``
     - PyPI trove classifiers
   * - ``repository_url``
     - ``null``
     - Source repository URL
   * - ``homepage_url``
     - ``null``
     - Project homepage URL
   * - ``documentation_url``
     - ``null``
     - Documentation site URL
   * - ``bug_tracker_url``
     - ``null``
     - Issue/bug tracker URL
   * - ``github_owner``
     - ``null``
     - GitHub owner/org name — auto-generates repository, homepage, and bug tracker URLs
   * - ``overwrite``
     - ``false``
     - Overwrite existing non-empty values (default: only fill blanks)

**migrate_to_uv** accepts these parameters:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``project_dir``
     - (required)
     - Path to the project to migrate
   * - ``dry_run``
     - ``false``
     - Preview changes without modifying files
   * - ``skip_lock``
     - ``false``
     - Skip locking dependencies with uv after migration
   * - ``skip_uv_checks``
     - ``false``
     - Skip checks for whether the project already uses uv
   * - ``ignore_locked_versions``
     - ``false``
     - Ignore current locked dependency versions
   * - ``replace_project_section``
     - ``false``
     - Replace existing ``[project]`` section instead of keeping existing fields
   * - ``keep_current_build_backend``
     - ``false``
     - Keep the current build backend
   * - ``keep_current_data``
     - ``false``
     - Keep data from current package manager (don't delete old files/sections)
   * - ``ignore_errors``
     - ``false``
     - Continue migration even if errors occur
   * - ``package_manager``
     - ``null``
     - Source package manager: ``poetry``, ``pipenv``, ``pip-tools``, or ``pip``.
       Auto-detected if omitted
   * - ``dependency_groups_strategy``
     - ``null``
     - Strategy for migrating dependency groups: ``set-default-groups-all``,
       ``set-default-groups``, ``include-in-dev``, ``keep-existing``, ``merge-into-dev``
   * - ``build_backend``
     - ``null``
     - Build backend to use: ``hatch`` or ``uv``

Available Resources
-------------------

Resources are read-only data the AI can access:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - URI
     - Description
   * - ``preset://list``
     - JSON list of all preset names and descriptions
   * - ``config://user``
     - JSON of current user config path and values
   * - ``template://list``
     - JSON list of available Jinja2 template filenames

Guided Prompts
--------------

Prompts provide guided workflows for multi-step tasks:

**create-project**
   Walks the AI through project creation: choosing a name, selecting a preset,
   configuring overrides (layout, package manager, type checker, Docker, docs,
   coverage, tox), selecting an output directory, and calling ``create_project``.
   Optionally validates the result with ``validate_project``.

**augment-project**
   Walks the AI through augmenting an existing project: confirming the directory,
   explaining all available components (test workflow, lint workflow, dependabot,
   tests directory, gitignore, codecov, documentation, tox, Dockerfile, devcontainer,
   PyPI publish), asking which to generate, and calling ``augment_project``.

Architecture
------------

The MCP server is a thin wrapper around pypreset's core modules — tools contain
no business logic and delegate to existing functions:

.. code-block:: text

   FastMCP server
       ├── tools.py       → calls preset_loader, generator, validator,
       │                     user_config, metadata_utils, act_runner, migration
       ├── resources.py   → calls preset_loader, user_config, template_engine
       └── prompts.py     → builds guided conversation flows

The server is built with `FastMCP <https://github.com/jlowin/fastmcp>`_ 3.x and uses
Pydantic ``Field`` annotations for tool parameter validation and documentation.

All tool handlers use lazy imports (``from pypreset.xxx import ...`` inside the
function body) to keep server startup fast and avoid circular imports.
