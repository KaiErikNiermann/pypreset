Presets
=======

Presets are YAML configuration files that define project templates. They control
which dependencies, templates, tooling, and structure a generated project will have.

Built-in Presets
----------------

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Name
     - Description
   * - ``empty-package``
     - A minimal Python package with standard tooling (pytest, ruff, dependabot)
   * - ``cli-tool``
     - A command-line tool built with Typer (extends ``empty-package``)
   * - ``data-science``
     - Data science project with Jupyter, pandas, and matplotlib
   * - ``discord-bot``
     - Discord bot using discord.py

List available presets:

.. code-block:: bash

   pysetup list-presets

Inspect a preset:

.. code-block:: bash

   pysetup show-preset cli-tool

Preset YAML Schema
------------------

A complete preset file has this structure:

.. code-block:: yaml

   name: my-preset
   description: Short description

   # Optional: inherit from another preset
   base: empty-package

   metadata:
     version: "0.1.0"
     description: "A Python package"
     python_version: "3.11"

   structure:
     directories: []       # Extra directories to create
     files:                 # Extra files to render from templates
       - path: "src/{{ project.package_name }}/cli.py"
         template: cli_main.py.j2

   dependencies:
     main:
       - "typer>=0.15.0"
     dev: []

   testing:
     enabled: true
     framework: pytest
     coverage: false

   formatting:
     enabled: true
     tool: ruff
     line_length: 100

   dependabot:
     enabled: true
     schedule: weekly
     open_pull_requests_limit: 5

   typing_level: strict     # none | basic | strict
   layout: src              # src | flat

   entry_points:
     - name: "__PROJECT_NAME__"
       module: "__PACKAGE_NAME__.cli:app"

   extras: {}               # Arbitrary key-value pairs for template use

Inheritance
-----------

Presets support single inheritance via the ``base:`` field. The child preset
inherits all values from the parent, then overrides with its own values.

.. code-block:: yaml

   # cli-tool.yaml inherits from empty-package.yaml
   base: empty-package

   dependencies:
     main:
       - "typer>=0.15.0"   # Added to parent's main deps

Key rules:

- **Scalars** (strings, booleans, numbers): child replaces parent
- **Lists**: child **extends** parent (additive merge via ``deep_merge``)
- **Dicts**: child merges into parent (recursive)
- Only single-level inheritance is supported (no chains of ``base:`` references)

Placeholders
~~~~~~~~~~~~

Two special placeholder strings are available in ``entry_points``:

- ``__PROJECT_NAME__`` — replaced with the hyphenated project name (e.g. ``my-app``)
- ``__PACKAGE_NAME__`` — replaced with the underscored package name (e.g. ``my_app``)

These are substituted at config build time by ``preset_loader._replace_placeholders()``.

Custom Presets
--------------

Place custom preset YAML files in:

.. code-block:: text

   ~/.config/pysetup/presets/

User presets take precedence over built-in presets with the same name. Use them
to define your organization's project templates:

.. code-block:: yaml

   # ~/.config/pysetup/presets/company-service.yaml
   name: company-service
   description: Internal microservice template

   base: empty-package

   metadata:
     python_version: "3.14"

   dependencies:
     main:
       - "fastapi>=0.115.0"
       - "uvicorn>=0.34.0"
     dev:
       - "httpx>=0.28.0"

   structure:
     files:
       - path: "Dockerfile"
         template: dockerfile.j2

Then use it:

.. code-block:: bash

   pysetup create my-service --preset company-service
