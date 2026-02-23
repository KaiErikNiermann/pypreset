"""Project analyzer - extracts metadata from existing Python projects."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]


logger = logging.getLogger(__name__)


class PackageManager(str, Enum):
    """Detected package manager."""

    POETRY = "poetry"
    PDM = "pdm"
    SETUPTOOLS = "setuptools"
    HATCH = "hatch"
    FLIT = "flit"
    UNKNOWN = "unknown"


class DetectedLinter(str, Enum):
    """Detected linting/formatting tools."""

    RUFF = "ruff"
    BLACK = "black"
    FLAKE8 = "flake8"
    ISORT = "isort"
    NONE = "none"


class DetectedTestFramework(str, Enum):
    """Detected testing framework."""

    PYTEST = "pytest"
    UNITTEST = "unittest"
    NONE = "none"


class DetectedTypeChecker(str, Enum):
    """Detected type checker."""

    MYPY = "mypy"
    PYRIGHT = "pyright"
    NONE = "none"


@dataclass
class AnalysisConfidence:
    """Confidence levels for detected values."""

    HIGH: Literal["high"] = "high"
    MEDIUM: Literal["medium"] = "medium"
    LOW: Literal["low"] = "low"


@dataclass
class DetectedValue[T]:
    """A detected value with confidence level."""

    value: T
    confidence: Literal["high", "medium", "low"]
    source: str  # Where this was detected from

    @property
    def is_reliable(self) -> bool:
        """Check if value is reliable enough to use without confirmation."""
        return self.confidence == "high"


@dataclass
class MissingField:
    """Represents a field that could not be detected."""

    name: str
    description: str
    required: bool
    default: Any = None
    choices: list[str] | None = None


@dataclass
class ProjectAnalysis:
    """Complete analysis of an existing project."""

    # Project identification
    project_name: DetectedValue[str] | None = None
    package_name: DetectedValue[str] | None = None
    version: DetectedValue[str] | None = None
    description: DetectedValue[str] | None = None
    python_version: DetectedValue[str] | None = None

    # Package management
    package_manager: DetectedValue[PackageManager] | None = None

    # Testing
    test_framework: DetectedValue[DetectedTestFramework] | None = None
    has_tests_dir: bool = False
    existing_tests: list[Path] = field(default_factory=list)

    # Linting/Formatting
    linter: DetectedValue[DetectedLinter] | None = None
    type_checker: DetectedValue[DetectedTypeChecker] | None = None
    line_length: DetectedValue[int] | None = None

    # GitHub workflows
    has_github_dir: bool = False
    existing_workflows: list[Path] = field(default_factory=list)
    has_dependabot: bool = False

    # Gitignore
    has_gitignore: bool = False

    # Structure
    has_src_layout: bool = False
    source_dirs: list[str] = field(default_factory=list)

    # Dependencies (for reference)
    main_dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)

    # Missing fields that need user input
    missing_fields: list[MissingField] = field(default_factory=list)

    def get_reliable_values(self) -> dict[str, Any]:
        """Get all values that are reliable enough to use without confirmation."""
        result: dict[str, Any] = {}
        for attr_name in [
            "project_name",
            "package_name",
            "version",
            "description",
            "python_version",
            "package_manager",
            "test_framework",
            "linter",
            "type_checker",
            "line_length",
        ]:
            detected = getattr(self, attr_name)
            if detected is not None and detected.is_reliable:
                result[attr_name] = detected.value
        return result

    def get_uncertain_values(self) -> dict[str, DetectedValue[Any]]:
        """Get values that were detected but need confirmation."""
        result: dict[str, DetectedValue[Any]] = {}
        for attr_name in [
            "project_name",
            "package_name",
            "version",
            "description",
            "python_version",
            "package_manager",
            "test_framework",
            "linter",
            "type_checker",
            "line_length",
        ]:
            detected = getattr(self, attr_name)
            if detected is not None and not detected.is_reliable:
                result[attr_name] = detected
        return result


class ProjectAnalyzer:
    """Analyzes an existing Python project to extract metadata and configuration."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir.absolute()
        self.pyproject_data: dict[str, Any] = {}

    def analyze(self) -> ProjectAnalysis:
        """Perform complete project analysis."""
        analysis = ProjectAnalysis()

        # Load pyproject.toml if it exists
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists():
            self._load_pyproject(pyproject_path)
        else:
            analysis.missing_fields.append(
                MissingField(
                    name="pyproject.toml",
                    description="No pyproject.toml found - project metadata cannot be detected",
                    required=True,
                )
            )
            return analysis

        # Detect package manager
        analysis.package_manager = self._detect_package_manager()

        # Extract project metadata
        analysis.project_name = self._extract_project_name()
        analysis.package_name = self._extract_package_name(analysis.project_name)
        analysis.version = self._extract_version()
        analysis.description = self._extract_description()
        analysis.python_version = self._extract_python_version()

        # Extract dependencies
        analysis.main_dependencies, analysis.dev_dependencies = self._extract_dependencies()

        # Detect testing setup
        analysis.test_framework = self._detect_test_framework(analysis.dev_dependencies)
        analysis.has_tests_dir = (self.project_dir / "tests").is_dir()
        analysis.existing_tests = self._find_existing_tests()

        # Detect linting/formatting
        analysis.linter = self._detect_linter(analysis.dev_dependencies)
        analysis.type_checker = self._detect_type_checker(analysis.dev_dependencies)
        analysis.line_length = self._detect_line_length()

        # Check GitHub structure
        github_dir = self.project_dir / ".github"
        analysis.has_github_dir = github_dir.is_dir()
        if analysis.has_github_dir:
            workflows_dir = github_dir / "workflows"
            if workflows_dir.is_dir():
                analysis.existing_workflows = list(workflows_dir.glob("*.yml")) + list(
                    workflows_dir.glob("*.yaml")
                )
            analysis.has_dependabot = (github_dir / "dependabot.yml").exists()

        # Check gitignore
        analysis.has_gitignore = (self.project_dir / ".gitignore").exists()

        # Check source layout
        analysis.has_src_layout = (self.project_dir / "src").is_dir()
        analysis.source_dirs = self._detect_source_dirs()

        # Determine missing required fields
        analysis.missing_fields = self._determine_missing_fields(analysis)

        return analysis

    def _load_pyproject(self, path: Path) -> None:
        """Load and parse pyproject.toml."""
        try:
            with open(path, "rb") as f:
                self.pyproject_data = tomllib.load(f)
        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")
            self.pyproject_data = {}

    def _detect_package_manager(self) -> DetectedValue[PackageManager]:
        """Detect which package manager is being used."""
        # Check for poetry
        if "tool" in self.pyproject_data and "poetry" in self.pyproject_data["tool"]:
            # Confirm with poetry.lock
            if (self.project_dir / "poetry.lock").exists():
                return DetectedValue(
                    PackageManager.POETRY, "high", "pyproject.toml [tool.poetry] + poetry.lock"
                )
            return DetectedValue(PackageManager.POETRY, "medium", "pyproject.toml [tool.poetry]")

        # Check for PDM
        if "tool" in self.pyproject_data and "pdm" in self.pyproject_data["tool"]:
            if (self.project_dir / "pdm.lock").exists():
                return DetectedValue(
                    PackageManager.PDM, "high", "pyproject.toml [tool.pdm] + pdm.lock"
                )
            return DetectedValue(PackageManager.PDM, "medium", "pyproject.toml [tool.pdm]")

        # Check for Hatch
        if "tool" in self.pyproject_data and "hatch" in self.pyproject_data["tool"]:
            return DetectedValue(PackageManager.HATCH, "medium", "pyproject.toml [tool.hatch]")

        # Check for Flit
        if "tool" in self.pyproject_data and "flit" in self.pyproject_data["tool"]:
            return DetectedValue(PackageManager.FLIT, "medium", "pyproject.toml [tool.flit]")

        # Check build-backend
        build_system = self.pyproject_data.get("build-system", {})
        build_backend = build_system.get("build-backend", "")

        if "poetry" in build_backend:
            return DetectedValue(PackageManager.POETRY, "medium", "build-backend")
        if "pdm" in build_backend:
            return DetectedValue(PackageManager.PDM, "medium", "build-backend")
        if "hatchling" in build_backend:
            return DetectedValue(PackageManager.HATCH, "medium", "build-backend")
        if "flit" in build_backend:
            return DetectedValue(PackageManager.FLIT, "medium", "build-backend")
        if "setuptools" in build_backend:
            return DetectedValue(PackageManager.SETUPTOOLS, "medium", "build-backend")

        return DetectedValue(PackageManager.UNKNOWN, "low", "no specific markers found")

    def _extract_project_name(self) -> DetectedValue[str] | None:
        """Extract project name from pyproject.toml."""
        # Try poetry section first
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        if "name" in poetry:
            return DetectedValue(poetry["name"], "high", "pyproject.toml [tool.poetry.name]")

        # Try project section (PEP 621)
        project = self.pyproject_data.get("project", {})
        if "name" in project:
            return DetectedValue(project["name"], "high", "pyproject.toml [project.name]")

        # Fall back to directory name
        return DetectedValue(self.project_dir.name, "low", "directory name")

    def _extract_package_name(
        self, project_name: DetectedValue[str] | None
    ) -> DetectedValue[str] | None:
        """Extract or derive package name."""
        # Check for explicit packages in poetry config
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        packages = poetry.get("packages", [])
        if packages and isinstance(packages[0], dict) and "include" in packages[0]:
            return DetectedValue(
                packages[0]["include"], "high", "pyproject.toml [tool.poetry.packages]"
            )

        # Look for packages in src directory
        src_dir = self.project_dir / "src"
        if src_dir.is_dir():
            packages_found = [
                d.name
                for d in src_dir.iterdir()
                if d.is_dir() and not d.name.startswith((".", "__"))
            ]
            if len(packages_found) == 1:
                return DetectedValue(packages_found[0], "high", "src directory structure")
            elif len(packages_found) > 1:
                return DetectedValue(
                    packages_found[0], "medium", "src directory (multiple packages)"
                )

        # Derive from project name
        if project_name:
            derived = project_name.value.replace("-", "_")
            return DetectedValue(
                derived, "medium", f"derived from project name: {project_name.value}"
            )

        return None

    def _extract_version(self) -> DetectedValue[str] | None:
        """Extract version from pyproject.toml."""
        # Try poetry section
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        if "version" in poetry:
            return DetectedValue(poetry["version"], "high", "pyproject.toml [tool.poetry.version]")

        # Try project section
        project = self.pyproject_data.get("project", {})
        if "version" in project:
            return DetectedValue(project["version"], "high", "pyproject.toml [project.version]")

        return DetectedValue("0.1.0", "low", "default value")

    def _extract_description(self) -> DetectedValue[str] | None:
        """Extract description from pyproject.toml."""
        # Try poetry section
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        if "description" in poetry:
            return DetectedValue(
                poetry["description"], "high", "pyproject.toml [tool.poetry.description]"
            )

        # Try project section
        project = self.pyproject_data.get("project", {})
        if "description" in project:
            return DetectedValue(
                project["description"], "high", "pyproject.toml [project.description]"
            )

        return None

    def _extract_python_version(self) -> DetectedValue[str] | None:
        """Extract minimum Python version."""
        # Try poetry section
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        deps = poetry.get("dependencies", {})
        python_spec = deps.get("python", "")

        if python_spec:
            version = self._parse_python_version_spec(python_spec)
            if version:
                return DetectedValue(
                    version, "high", "pyproject.toml [tool.poetry.dependencies.python]"
                )

        # Try project section (PEP 621)
        project = self.pyproject_data.get("project", {})
        requires_python = project.get("requires-python", "")
        if requires_python:
            version = self._parse_python_version_spec(requires_python)
            if version:
                return DetectedValue(version, "high", "pyproject.toml [project.requires-python]")

        # Check ruff target-version
        ruff = self.pyproject_data.get("tool", {}).get("ruff", {})
        target_version = ruff.get("target-version", "")
        if target_version:
            # Convert py311 -> 3.11
            match = re.match(r"py(\d)(\d+)", target_version)
            if match:
                version = f"{match.group(1)}.{match.group(2)}"
                return DetectedValue(version, "medium", "pyproject.toml [tool.ruff.target-version]")

        # Check mypy python_version
        mypy = self.pyproject_data.get("tool", {}).get("mypy", {})
        mypy_version = mypy.get("python_version", "")
        if mypy_version:
            return DetectedValue(
                str(mypy_version), "medium", "pyproject.toml [tool.mypy.python_version]"
            )

        return DetectedValue("3.11", "low", "default value")

    def _parse_python_version_spec(self, spec: str) -> str | None:
        """Parse a Python version specifier to extract the base version."""
        # Handle common patterns: ^3.11, >=3.11, ~3.11, 3.11.*, ==3.11, >=3.11,<4
        patterns = [
            r"[>=^~]*(\d+\.\d+)",  # ^3.11, >=3.11, ~3.11
            r"(\d+\.\d+)\.\*",  # 3.11.*
            r"==(\d+\.\d+)",  # ==3.11
        ]
        for pattern in patterns:
            match = re.search(pattern, spec)
            if match:
                return match.group(1)
        return None

    def _extract_dependencies(self) -> tuple[list[str], list[str]]:
        """Extract main and dev dependencies."""
        main_deps: list[str] = []
        dev_deps: list[str] = []

        # Poetry format
        poetry = self.pyproject_data.get("tool", {}).get("poetry", {})
        if poetry:
            deps = poetry.get("dependencies", {})
            main_deps = [k for k in deps if k != "python"]

            # Dev dependencies can be in various groups
            dev_group = poetry.get("group", {}).get("dev", {}).get("dependencies", {})
            dev_deps = list(dev_group.keys())

            # Also check old-style dev-dependencies
            old_dev = poetry.get("dev-dependencies", {})
            dev_deps.extend(old_dev.keys())

        # PEP 621 format
        project = self.pyproject_data.get("project", {})
        if project:
            deps = project.get("dependencies", [])
            main_deps.extend([self._parse_dep_name(d) for d in deps])

            optional = project.get("optional-dependencies", {})
            for group in ["dev", "test", "development"]:
                if group in optional:
                    dev_deps.extend([self._parse_dep_name(d) for d in optional[group]])

        return list(set(main_deps)), list(set(dev_deps))

    def _parse_dep_name(self, dep_string: str) -> str:
        """Parse dependency name from a requirement string."""
        # Handle: package, package>=1.0, package[extra], package[extra]>=1.0
        match = re.match(r"([a-zA-Z0-9_-]+)", dep_string)
        return match.group(1) if match else dep_string

    def _detect_test_framework(self, dev_deps: list[str]) -> DetectedValue[DetectedTestFramework]:
        """Detect testing framework from dependencies and config."""
        # Check dependencies
        dep_names_lower = [d.lower() for d in dev_deps]

        if "pytest" in dep_names_lower:
            # Confirm with pytest config
            if "tool" in self.pyproject_data and "pytest" in self.pyproject_data["tool"]:
                return DetectedValue(
                    DetectedTestFramework.PYTEST, "high", "dependencies + [tool.pytest]"
                )
            return DetectedValue(DetectedTestFramework.PYTEST, "high", "pytest in dependencies")

        # Check for pytest.ini or conftest.py
        if (self.project_dir / "pytest.ini").exists() or (
            self.project_dir / "conftest.py"
        ).exists():
            return DetectedValue(
                DetectedTestFramework.PYTEST, "medium", "pytest.ini or conftest.py exists"
            )

        if (self.project_dir / "tests" / "conftest.py").exists():
            return DetectedValue(DetectedTestFramework.PYTEST, "medium", "tests/conftest.py exists")

        return DetectedValue(DetectedTestFramework.NONE, "medium", "no test framework detected")

    def _find_existing_tests(self) -> list[Path]:
        """Find existing test files."""
        tests_dir = self.project_dir / "tests"
        if not tests_dir.is_dir():
            return []
        return list(tests_dir.glob("test_*.py"))

    def _detect_linter(self, dev_deps: list[str]) -> DetectedValue[DetectedLinter]:
        """Detect linting/formatting tools."""
        dep_names_lower = [d.lower() for d in dev_deps]

        # Check for ruff
        if (
            "ruff" in dep_names_lower
            or "tool" in self.pyproject_data
            and "ruff" in self.pyproject_data["tool"]
        ):
            if "tool" in self.pyproject_data and "ruff" in self.pyproject_data["tool"]:
                return DetectedValue(DetectedLinter.RUFF, "high", "ruff in config + dependencies")
            return DetectedValue(DetectedLinter.RUFF, "high", "ruff in dependencies")

        # Check for black
        if (
            "black" in dep_names_lower
            or "tool" in self.pyproject_data
            and "black" in self.pyproject_data["tool"]
        ):
            return DetectedValue(DetectedLinter.BLACK, "high", "black in dependencies/config")

        # Check for flake8
        if "flake8" in dep_names_lower:
            return DetectedValue(DetectedLinter.FLAKE8, "medium", "flake8 in dependencies")

        return DetectedValue(DetectedLinter.NONE, "medium", "no linter detected")

    def _detect_type_checker(self, dev_deps: list[str]) -> DetectedValue[DetectedTypeChecker]:
        """Detect type checker."""
        dep_names_lower = [d.lower() for d in dev_deps]

        if (
            "mypy" in dep_names_lower
            or "tool" in self.pyproject_data
            and "mypy" in self.pyproject_data["tool"]
        ):
            if "tool" in self.pyproject_data and "mypy" in self.pyproject_data["tool"]:
                return DetectedValue(
                    DetectedTypeChecker.MYPY, "high", "mypy in config + dependencies"
                )
            return DetectedValue(DetectedTypeChecker.MYPY, "high", "mypy in dependencies")

        if (
            "pyright" in dep_names_lower
            or "tool" in self.pyproject_data
            and "pyright" in self.pyproject_data["tool"]
        ):
            return DetectedValue(
                DetectedTypeChecker.PYRIGHT, "high", "pyright in dependencies/config"
            )

        return DetectedValue(DetectedTypeChecker.NONE, "medium", "no type checker detected")

    def _detect_line_length(self) -> DetectedValue[int] | None:
        """Detect configured line length."""
        # Check ruff
        ruff = self.pyproject_data.get("tool", {}).get("ruff", {})
        if "line-length" in ruff:
            return DetectedValue(
                ruff["line-length"], "high", "pyproject.toml [tool.ruff.line-length]"
            )

        # Check black
        black = self.pyproject_data.get("tool", {}).get("black", {})
        if "line-length" in black:
            return DetectedValue(
                black["line-length"], "high", "pyproject.toml [tool.black.line-length]"
            )

        return DetectedValue(100, "low", "default value")

    def _detect_source_dirs(self) -> list[str]:
        """Detect source directories."""
        dirs: list[str] = []

        if (self.project_dir / "src").is_dir():
            dirs.append("src")

        # Check for top-level package directories
        for item in self.project_dir.iterdir():
            is_package = (
                item.is_dir()
                and not item.name.startswith((".", "_"))
                and (item / "__init__.py").exists()
            )
            if is_package:
                dirs.append(item.name)

        return dirs

    def _determine_missing_fields(self, analysis: ProjectAnalysis) -> list[MissingField]:
        """Determine which fields are missing and need user input."""
        missing: list[MissingField] = []

        if analysis.project_name is None:
            missing.append(
                MissingField(
                    name="project_name",
                    description="Project name",
                    required=True,
                )
            )

        if analysis.python_version is None or analysis.python_version.confidence == "low":
            missing.append(
                MissingField(
                    name="python_version",
                    description="Minimum Python version",
                    required=True,
                    default="3.11",
                    choices=["3.10", "3.11", "3.12", "3.13"],
                )
            )

        if (
            analysis.test_framework is None
            or analysis.test_framework.value == DetectedTestFramework.NONE
        ):
            missing.append(
                MissingField(
                    name="test_framework",
                    description="Testing framework to use",
                    required=False,
                    default="pytest",
                    choices=["pytest", "unittest", "none"],
                )
            )

        if analysis.linter is None or analysis.linter.value == DetectedLinter.NONE:
            missing.append(
                MissingField(
                    name="linter",
                    description="Linting/formatting tool",
                    required=False,
                    default="ruff",
                    choices=["ruff", "black", "none"],
                )
            )

        return missing


def analyze_project(project_dir: Path) -> ProjectAnalysis:
    """Convenience function to analyze a project."""
    analyzer = ProjectAnalyzer(project_dir)
    return analyzer.analyze()
