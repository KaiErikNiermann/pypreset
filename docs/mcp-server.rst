MCP Server
==========

pypreset includes an `MCP <https://modelcontextprotocol.io/>`_ (Model Context Protocol)
server that lets AI coding assistants create projects, augment existing ones,
list presets, validate structure, and manage configuration — all programmatically.

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
       package manager, typing level, Python version)
   * - ``augment_project``
     - Add CI workflows, tests, gitignore, and dependabot to an existing project.
       Auto-detects tooling from ``pyproject.toml``
   * - ``validate_project``
     - Check structural correctness of a generated project directory
   * - ``list_presets``
     - List all available presets with names and descriptions
   * - ``show_preset``
     - Show the full YAML configuration of a specific preset
   * - ``get_user_config``
     - Read current user-level defaults from ``~/.config/pypreset/config.yaml``
   * - ``set_user_config``
     - Update user-level defaults (merges into existing config)

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

Prompts provide guided workflows:

**create-project**
   Walks the AI through project creation: choosing a name, selecting a preset,
   configuring overrides, and calling ``create_project``.

**augment-project**
   Walks the AI through augmenting an existing project: confirming the directory,
   selecting components to add, and calling ``augment_project``.

Architecture
------------

The MCP server is a thin wrapper around pypreset's core modules:

.. code-block:: text

   FastMCP server
       ├── tools.py       → calls preset_loader, generator, validator, user_config
       ├── resources.py   → calls preset_loader, user_config, template_engine
       └── prompts.py     → builds guided conversation flows

The server is built with `FastMCP <https://github.com/jlowin/fastmcp>`_ and uses
Pydantic ``Field`` annotations for tool parameter validation and documentation.

All tool handlers use lazy imports (``from pypreset.xxx import ...`` inside the
function body) to keep server startup fast and avoid circular imports.
