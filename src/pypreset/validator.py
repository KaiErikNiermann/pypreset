"""Project validation utilities."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, passed: bool, message: str, details: str | None = None) -> None:
        self.passed = passed
        self.message = message
        self.details = details

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        status = "✓" if self.passed else "✗"
        return f"{status} {self.message}"


class ProjectValidator:
    """Validates that a generated project is structurally sound."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.results: list[ValidationResult] = []

    def validate_all(self) -> list[ValidationResult]:
        """Run all validation checks."""
        self.results = []

        self.results.append(self._check_project_exists())
        self.results.append(self._check_pyproject_toml())
        self.results.append(self._check_src_layout())
        self.results.append(self._check_package_init())
        self.results.append(self._check_readme())
        self.results.append(self._check_gitignore())
        self.results.append(self._check_pyproject_toml_valid())

        return self.results

    def is_valid(self) -> bool:
        """Check if all validations passed."""
        if not self.results:
            self.validate_all()
        return all(self.results)

    def _check_project_exists(self) -> ValidationResult:
        """Check that the project directory exists."""
        if self.project_dir.exists() and self.project_dir.is_dir():
            return ValidationResult(True, "Project directory exists")
        return ValidationResult(False, "Project directory does not exist")

    def _check_pyproject_toml(self) -> ValidationResult:
        """Check that pyproject.toml exists."""
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists():
            return ValidationResult(True, "pyproject.toml exists")
        return ValidationResult(False, "pyproject.toml is missing")

    def _check_src_layout(self) -> ValidationResult:
        """Check that a valid package layout (src or flat) is present."""
        src_dir = self.project_dir / "src"
        if src_dir.exists() and src_dir.is_dir():
            packages = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if packages:
                pkg_names = [p.name for p in packages]
                return ValidationResult(True, f"src-layout with package(s): {pkg_names}")
            return ValidationResult(False, "src directory exists but no packages found")

        # Check for flat layout: top-level directories with __init__.py
        _non_package_dirs = {
            "tests",
            "docs",
            "scripts",
            "data",
            "notebooks",
            "models",
            "reports",
        }
        if self.project_dir.exists():
            flat_packages = [
                d
                for d in self.project_dir.iterdir()
                if d.is_dir()
                and not d.name.startswith((".", "_"))
                and d.name not in _non_package_dirs
                and (d / "__init__.py").exists()
            ]
            if flat_packages:
                pkg_names = [p.name for p in flat_packages]
                return ValidationResult(True, f"flat-layout with package(s): {pkg_names}")

        return ValidationResult(
            False,
            "No package directory found (neither src-layout nor flat-layout)",
        )

    def _check_package_init(self) -> ValidationResult:
        """Check that package __init__.py exists."""
        src_dir = self.project_dir / "src"

        # Try src-layout first
        if src_dir.exists():
            packages = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if packages:
                for package in packages:
                    init_file = package / "__init__.py"
                    if not init_file.exists():
                        return ValidationResult(False, f"__init__.py missing in src/{package.name}")
                return ValidationResult(True, "All packages have __init__.py")

        # Try flat-layout
        _non_package_dirs = {
            "tests",
            "docs",
            "scripts",
            "data",
            "notebooks",
            "models",
            "reports",
        }
        if self.project_dir.exists():
            flat_packages = [
                d
                for d in self.project_dir.iterdir()
                if d.is_dir()
                and not d.name.startswith((".", "_"))
                and d.name not in _non_package_dirs
                and (d / "__init__.py").exists()
            ]
            if flat_packages:
                return ValidationResult(True, "All packages have __init__.py")

        return ValidationResult(False, "No packages with __init__.py found")

    def _check_readme(self) -> ValidationResult:
        """Check that README.md exists."""
        readme_path = self.project_dir / "README.md"
        if readme_path.exists():
            return ValidationResult(True, "README.md exists")
        return ValidationResult(False, "README.md is missing")

    def _check_gitignore(self) -> ValidationResult:
        """Check that .gitignore exists."""
        gitignore_path = self.project_dir / ".gitignore"
        if gitignore_path.exists():
            return ValidationResult(True, ".gitignore exists")
        return ValidationResult(False, ".gitignore is missing")

    def _check_pyproject_toml_valid(self) -> ValidationResult:
        """Check that pyproject.toml is valid TOML."""
        pyproject_path = self.project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            return ValidationResult(False, "Cannot validate: pyproject.toml missing")

        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                tomllib.load(f)
            return ValidationResult(True, "pyproject.toml is valid TOML")
        except Exception as e:
            return ValidationResult(False, f"pyproject.toml is invalid: {e}")


def validate_project(project_dir: Path) -> tuple[bool, list[ValidationResult]]:
    """Validate a project directory.

    Returns:
        Tuple of (is_valid, list of validation results)
    """
    validator = ProjectValidator(project_dir)
    results = validator.validate_all()
    return validator.is_valid(), results


def validate_with_poetry(project_dir: Path) -> ValidationResult:
    """Validate project using poetry check."""
    try:
        result = subprocess.run(
            ["poetry", "check"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return ValidationResult(True, "poetry check passed", result.stdout)
        return ValidationResult(False, "poetry check failed", result.stderr)
    except FileNotFoundError:
        return ValidationResult(False, "poetry not found", "Cannot run poetry check")
    except Exception as e:
        return ValidationResult(False, f"poetry check error: {e}")
