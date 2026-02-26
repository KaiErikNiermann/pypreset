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
     - GitHub Actions CI for Poetry projects (test + lint jobs)
   * - ``github_ci_uv.yaml.j2``
     - GitHub Actions CI for uv projects (uses ``astral-sh/setup-uv``)
   * - ``dependabot.yml.j2``
     - Dependabot configuration (pip + GitHub Actions ecosystems)
   * - ``docs_workflow.yaml.j2``
     - GitHub Pages deployment workflow for documentation

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
     - Multi-stage Dockerfile for Poetry projects (src and flat layout aware)
   * - ``Dockerfile_uv.j2``
     - Multi-stage Dockerfile for uv projects
   * - ``dockerignore.j2``
     - ``.dockerignore``
   * - ``devcontainer.json.j2``
     - ``.devcontainer/devcontainer.json`` (VS Code Dev Container with package-manager-aware extensions)

**Documentation templates:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``sphinx_conf.py.j2``
     - Sphinx ``docs/conf.py`` (RTD theme)
   * - ``docs_index.rst.j2``
     - Sphinx ``docs/index.rst``
   * - ``mkdocs.yml.j2``
     - MkDocs ``mkdocs.yml`` (Material theme)
   * - ``docs_index.md.j2``
     - MkDocs ``docs/index.md``

**Configuration templates:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``pre-commit-config.yaml.j2``
     - ``.pre-commit-config.yaml``
   * - ``codecov.yml.j2``
     - ``codecov.yml`` with configurable thresholds and ignore patterns
   * - ``tox.ini.j2``
     - ``tox.ini`` with tox-uv backend

**Augment templates** (in ``templates/augment/``):

Used by ``pypreset augment`` to add components to existing projects. These are
separate from the create templates because they need to adapt to the detected
tooling of an existing project rather than using preset-defined settings.

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Template
     - Output
   * - ``test_workflow.yaml.j2``
     - GitHub Actions test workflow (adapts to detected package manager and test framework)
   * - ``lint_workflow.yaml.j2``
     - GitHub Actions lint workflow (adapts to detected linter and type checker)
   * - ``dependabot_augment.yml.j2``
     - Dependabot configuration
   * - ``test_template.py.j2``
     - Template test file for ``tests/``
   * - ``conftest.py.j2``
     - pytest ``conftest.py`` with shared fixtures
   * - ``pypi_publish_workflow.yaml.j2``
     - PyPI publish workflow using OIDC trusted publishing
   * - ``gitignore.j2``
     - Python-specific ``.gitignore``

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

   {# Documentation #}
   {% if documentation.enabled %}
   {{ documentation.tool }}         {# "sphinx" or "mkdocs" #}
   {{ documentation.deploy_gh_pages }}
   {% endif %}

   {# Extras dict (preset-specific data) #}
   {{ project.extras.cli_framework }}  {# "typer" for cli-tool preset #}

Package Manager Selection
-------------------------

The generator picks template variants based on ``project.package_manager``:

- **Poetry** (default): ``pyproject.toml.j2`` + ``github_ci.yaml.j2`` + ``Dockerfile.j2``
- **uv**: ``pyproject_uv.toml.j2`` + ``github_ci_uv.yaml.j2`` + ``Dockerfile_uv.j2``

The uv variant uses PEP 621 ``[project]`` tables with ``hatchling`` as the build
backend, and CI workflows use ``astral-sh/setup-uv`` instead of ``snok/install-poetry``.

README Template
---------------

The ``README.md.j2`` template generates a full README with badges, installation
instructions, usage examples, a features list, and development commands. It is
used by both the ``create`` and ``augment`` pipelines.

**Key context variables used by the template:**

- ``project.name``, ``project.description``, ``project.repository_url``, ``project.license``
- ``testing.enabled``, ``testing.coverage_config.enabled``
- ``formatting.tool``, ``formatting.type_checker``
- ``typing_level`` (``"none"``, ``"basic"``, or ``"strict"``)
- ``entry_points`` (list of ``{name, module}`` dicts)
- ``docker.enabled``, ``docker.devcontainer``
- ``documentation.enabled``, ``documentation.tool``
- ``package_manager`` (``"poetry"`` or ``"uv"``)

**Badge generation** relies on ``project.repository_url`` containing a GitHub URL.
When present, CI, PyPI version, Python version, and (optionally) Codecov badges
are rendered. A license badge is added when ``project.license`` is set.

**Preset override:** set ``metadata.readme_template`` in a preset YAML to use a
custom template instead of the default ``README.md.j2``:

.. code-block:: yaml

   metadata:
     readme_template: my_readme.j2

The ``pypreset badges`` CLI command and the ``generate_badges`` MCP tool provide
standalone badge generation from ``pyproject.toml`` without rendering the full
README template.

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
