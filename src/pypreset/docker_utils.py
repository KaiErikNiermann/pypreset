"""Docker utilities for resolving base images."""


def resolve_docker_base_image(python_version: str, base_image: str | None = None) -> str:
    """Resolve the Docker base image for a project.

    Returns base_image if provided, otherwise derives from python_version.
    """
    if base_image:
        return base_image
    return f"python:{python_version}-slim"
