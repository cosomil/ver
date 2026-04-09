import os
from pathlib import Path


def find_root_dir() -> Path:
    current_dir = Path(os.getcwd())
    while current_dir != current_dir.parent:
        if (current_dir / "pyproject.toml").exists():
            return current_dir
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory.")
