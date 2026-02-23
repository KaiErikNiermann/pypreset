Architecture
============

Overview
--------

pypreset has two primary workflows: **create** (scaffold a new project) and
**augment** (add components to an existing project). Both are driven by YAML
preset configurations and Jinja2 templates.

Create Command Flow
-------------------

.. code-block:: text

   CLI args → OverrideOptions
       ↓
   preset_loader.build_project_config()
       ├── load_preset() → YAML file
       ├── resolve_preset_chain() → deep_merge inheritance
       ├── apply_user_defaults() → ~/.config/pypreset/config.yaml
       ├── apply_overrides() → CLI flags (highest priority)
       └── _replace_placeholders() → __PROJECT_NAME__ / __PACKAGE_NAME__
       ↓
   ProjectConfig (Pydantic model)
       ↓
   generator.ProjectGenerator
       ├── Creates directories
       ├── Renders Jinja2 templates → pyproject.toml, workflows, etc.
       ├── Optionally generates Dockerfile/.dockerignore (or Containerfile for Podman)
       ├── Optionally generates .devcontainer/devcontainer.json
       ├── Optionally generates codecov.yml
       ├── Optionally generates documentation scaffold (MkDocs or Sphinx)
       ├── Optionally generates tox.ini (with tox-uv backend)
       ├── Optionally runs git init
       └── Optionally runs poetry install / uv sync
       ↓
   validator.validate_project() → structural checks

Augment Command Flow
--------------------

.. code-block:: text

   project_analyzer.analyze_project()
       ├── Reads pyproject.toml
       └── Detects: package manager, linter, test framework, type checker
       ↓
   interactive_prompts (or --auto)
       └── Fills in values the analyzer couldn't detect
       ↓
   AugmentConfig (dataclass)
       ↓
   augment_generator.AugmentOrchestrator
       ├── TestWorkflowGenerator
       ├── LintWorkflowGenerator
       ├── DependabotGenerator
       ├── TestsDirectoryGenerator
       ├── GitignoreGenerator
       ├── PypiPublishWorkflowGenerator
       ├── DockerfileGenerator
       ├── DevcontainerGenerator
       ├── CodecovGenerator
       ├── DocumentationGenerator
       └── ToxGenerator
       ↓
   AugmentResult (files created / skipped / errors)

Configuration Priority
----------------------

From lowest to highest priority:

1. **User defaults** — ``~/.config/pypreset/config.yaml`` via ``apply_user_defaults()``
2. **Preset config** — YAML preset files with single inheritance via ``base:``
3. **CLI overrides** — ``--layout``, ``--type-checker``, ``--package-manager``, etc.

Key Modules
-----------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Module
     - Purpose
   * - ``models.py``
     - Pydantic models (``ProjectConfig``, ``PresetConfig``, ``OverrideOptions``),
       enums (``LayoutStyle``, ``TypeChecker``, ``CreationPackageManager``,
       ``ContainerRuntime``, ``CoverageTool``, ``DocumentationTool``),
       and ``Partial*`` variants for preset merging
   * - ``preset_loader.py``
     - YAML loading, preset inheritance (``deep_merge``), placeholder substitution
   * - ``template_engine.py``
     - Jinja2 environment setup; ``get_template_context()`` builds the dict
       available in all ``.j2`` templates
   * - ``generator.py``
     - ``ProjectGenerator`` class; selects templates based on ``package_manager``
   * - ``augment_generator.py``
     - Component generators for augmenting existing projects
   * - ``project_analyzer.py``
     - Heuristic detection of tooling from ``pyproject.toml``
   * - ``docker_utils.py``
     - Helper to resolve Docker base images from ``python_version``
   * - ``user_config.py``
     - User-level defaults from ``~/.config/pypreset/config.yaml``
   * - ``validator.py``
     - Project structure validation
   * - ``versioning.py``
     - ``VersioningAssistant``; wraps ``poetry version``, git, and ``gh`` CLI
   * - ``mcp_server/``
     - MCP server subpackage for AI assistant integration

Preset System
-------------

- Built-in presets live in ``src/pypreset/presets/*.yaml``
- User presets in ``~/.config/pypreset/presets/`` take precedence
- Presets support single inheritance via the ``base:`` field
- ``deep_merge`` is **additive** for lists — child extends parent, not replaces
- ``__PROJECT_NAME__`` and ``__PACKAGE_NAME__`` are placeholder strings replaced
  in entry points at config build time

Template System
---------------

Jinja2 templates in ``src/pypreset/templates/`` receive a context dict built by
``template_engine.get_template_context()``. Template names referenced in preset
YAML ``files[].template`` fields must match filenames in this directory.

Key templates come in pairs for different package managers:

- ``pyproject.toml.j2`` (Poetry) / ``pyproject_uv.toml.j2`` (uv + hatchling)
- ``github_ci.yaml.j2`` (Poetry) / ``github_ci_uv.yaml.j2`` (uv + astral-sh/setup-uv)

Package Manager Abstraction
---------------------------

The ``CreationPackageManager`` enum (``poetry`` / ``uv``) controls which template
variant is rendered. The generator selects the correct ``pyproject.toml`` template
and CI workflow based on this value. The augment system detects the package manager
from the existing ``pyproject.toml`` via ``project_analyzer``.
