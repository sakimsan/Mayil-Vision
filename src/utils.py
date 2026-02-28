import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).parent.parent.parent

def get_project_dir(project_name: str, create: bool = True) -> dict:
    """
    Returns and optionally creates the directory structure for a specific project.
    """
    project_path = BASE_DIR / "data" / "projects" / project_name
    paths = {
        "root": project_path,
        "raw": project_path / "raw",
        "processed": project_path / "processed"
    }

    if create:
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

    return paths