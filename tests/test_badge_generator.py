"""Tests for the badge generator module."""

from pypreset.badge_generator import Badge, generate_badges


class TestGenerateBadges:
    """Tests for generate_badges()."""

    def test_github_badges_from_url(self) -> None:
        """Test that CI, PyPI, and Python badges are generated from a GitHub URL."""
        badges = generate_badges(
            "my-project",
            repository_url="https://github.com/owner/my-project",
        )

        labels = [b.label for b in badges]
        assert "CI" in labels
        assert "PyPI" in labels
        assert "Python" in labels

    def test_ci_badge_content(self) -> None:
        """Test CI badge markdown content."""
        badges = generate_badges(
            "my-project",
            repository_url="https://github.com/owner/my-project",
        )

        ci_badge = next(b for b in badges if b.label == "CI")
        assert "owner/my-project" in ci_badge.markdown
        assert "ci.yaml" in ci_badge.markdown

    def test_license_badge(self) -> None:
        """Test that license badge is generated."""
        badges = generate_badges("my-project", license_id="MIT")

        assert len(badges) == 1
        assert badges[0].label == "License"
        assert "MIT" in badges[0].markdown

    def test_license_with_dashes_escaped(self) -> None:
        """Test that dashes in license ID are escaped for shields.io."""
        badges = generate_badges("my-project", license_id="Apache-2.0")

        license_badge = next(b for b in badges if b.label == "License")
        assert "Apache--2.0" in license_badge.markdown

    def test_codecov_badge_requires_github_and_coverage(self) -> None:
        """Test that Codecov badge requires both a GitHub URL and coverage enabled."""
        badges = generate_badges(
            "my-project",
            repository_url="https://github.com/owner/my-project",
            has_coverage=True,
        )

        labels = [b.label for b in badges]
        assert "Codecov" in labels

    def test_no_codecov_without_github(self) -> None:
        """Test that Codecov badge is not generated without a GitHub URL."""
        badges = generate_badges("my-project", has_coverage=True)

        labels = [b.label for b in badges]
        assert "Codecov" not in labels

    def test_no_badges_with_no_inputs(self) -> None:
        """Test that no badges are generated when no inputs are provided."""
        badges = generate_badges("my-project")

        assert badges == []

    def test_all_badges_together(self) -> None:
        """Test generating all badge types at once."""
        badges = generate_badges(
            "my-project",
            repository_url="https://github.com/owner/my-project",
            license_id="MIT",
            has_coverage=True,
            python_version="3.12",
        )

        labels = [b.label for b in badges]
        assert labels == ["CI", "PyPI", "Python", "License", "Codecov"]

    def test_badge_is_frozen_dataclass(self) -> None:
        """Test that Badge instances are immutable."""
        badge = Badge(label="CI", markdown="text")
        assert badge.label == "CI"
        assert badge.markdown == "text"
