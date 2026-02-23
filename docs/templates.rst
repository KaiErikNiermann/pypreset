Templates
=========

pypreset uses `Jinja2 <https://jinja.palletsprojects.com/>`_ templates to generate
project files. Templates live in ``src/pypreset/templates/`` and are referenced by
preset YAML files.

Available Templates
-------------------

**Core project files:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``pyproject.toml.j2``
     - Poetry-based ``pyproject.toml``
   * - ``pyproject_uv.toml.j2``
     - uv/hatchling-based ``pyproject.toml`` (PEP 621 ``[project]`` table)
   * - ``README.md.j2``
     - Project README
   * - ``gitignore.j2``
     - ``.gitignore``

**CI workflows (Poetry vs uv pairs):**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``github_ci.yaml.j2``
     - GitHub Actions CI for Poetry projects
   * - ``github_ci_uv.yaml.j2``
     - GitHub Actions CI for uv projects (uses ``astral-sh/setup-uv``)
   * - ``dependabot.yml.j2``
     - Dependabot configuration

**Preset-specific templates:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Used by
   * - ``cli_main.py.j2``
     - ``cli-tool`` preset — Typer CLI entry point
   * - ``discord_bot.py.j2``
     - ``discord-bot`` preset — bot skeleton
   * - ``data_loader.py.j2``
     - ``data-science`` preset — data loading utilities
   * - ``notebook_exploration.ipynb.j2``
     - ``data-science`` preset — Jupyter notebook

**Docker & devcontainer templates:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``Dockerfile.j2``
     - Multi-stage Dockerfile for Poetry projects
   * - ``Dockerfile_uv.j2``
     - Multi-stage Dockerfile for uv projects
   * - ``dockerignore.j2``
     - ``.dockerignore``
   * - ``devcontainer.json.j2``
     - ``.devcontainer/devcontainer.json`` (VS Code Dev Container)

**Configuration templates:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``pre-commit-config.yaml.j2``
     - ``.pre-commit-config.yaml``

**Augment templates** (in ``templates/augment/``):

Used by ``pypreset augment`` to add components to existing projects. These include
CI workflow templates for various package managers and a PyPI publish workflow.

Template Context
----------------

All templates receive a context dict built by ``template_engine.get_template_context()``.
The primary variable is ``project``, which is the ``ProjectConfig`` Pydantic model
serialized to a dict:

.. code-block:: jinja

   {{ project.name }}              {# "my-app" #}
   {{ project.package_name }}      {# "my_app" #}
   {{ project.metadata.version }}  {# "0.1.0" #}
   {{ project.layout }}            {# "src" or "flat" #}
   {{ project.package_manager }}   {# "poetry" or "uv" #}

   {# Dependencies #}
   {% for dep in project.dependencies.main %}
   {{ dep }}
   {% endfor %}

   {# Testing #}
   {% if project.testing.enabled %}
   {{ project.testing.framework }}  {# "pytest" #}
   {% endif %}

   {# Type checker #}
   {{ project.type_checker }}       {# "mypy", "ty", or "none" #}
   {{ project.typing_level }}       {# "none", "basic", or "strict" #}

   {# Entry points #}
   {% for ep in project.entry_points %}
   {{ ep.name }} = {{ ep.module }}
   {% endfor %}

   {# Docker #}
   {% if docker.enabled %}
   {{ docker.base_image }}      {# "python:3.11-slim" (auto-resolved) #}
   {{ docker.devcontainer }}    {# true or false #}
   {% endif %}

   {# Extras dict (preset-specific data) #}
   {{ project.extras.cli_framework }}  {# "typer" for cli-tool preset #}

Package Manager Selection
-------------------------

The generator picks template variants based on ``project.package_manager``:

- **Poetry** (default): ``pyproject.toml.j2`` + ``github_ci.yaml.j2``
- **uv**: ``pyproject_uv.toml.j2`` + ``github_ci_uv.yaml.j2``

The uv variant uses PEP 621 ``[project]`` tables with ``hatchling`` as the build
backend, and CI workflows use ``astral-sh/setup-uv`` instead of ``snok/install-poetry``.

Writing Custom Templates
-------------------------

1. Create a ``.j2`` file in ``src/pypreset/templates/``
2. Reference it in a preset YAML under ``structure.files[].template``
3. Use the ``project`` context variable for all project metadata

Example preset entry:

.. code-block:: yaml

   structure:
     files:
       - path: "src/{{ project.package_name }}/config.py"
         template: config.py.j2

The ``path`` field itself is a Jinja2 expression, so you can use template
variables like ``{{ project.package_name }}`` in file paths.
