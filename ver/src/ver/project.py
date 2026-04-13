from dataclasses import dataclass, field
from pathlib import Path
import os
import subprocess
import tomllib
from typing import Any

PYPROJECT_TOML = "pyproject.toml"


@dataclass
class Project:
    name: str
    version: str
    tool: dict[str, Any] = field(default_factory=dict)

    def get_tool_config(self, name: str) -> dict[str, Any] | None:
        value = self.tool.get(name)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError(f"tool.{name} must be a table")
        return value


def find_root_dir() -> Path:
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        if (current_dir / PYPROJECT_TOML).exists():
            return current_dir
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory.")


def _resolve_project_path(path: str | Path | None = None) -> Path:
    if path is None:
        return find_root_dir() / PYPROJECT_TOML

    path = Path(path)
    if path.is_dir():
        return path / PYPROJECT_TOML

    return path


def _require_table(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} in {path} must be a table")
    return value


def _project_from_data(data: dict[str, Any], path: Path) -> Project:
    project = _require_table(data, "project", path)

    name = project.get("name")
    if not isinstance(name, str):
        raise ValueError(f"project.name in {path} must be a string")

    version = project.get("version")
    if not isinstance(version, str):
        raise ValueError(f"project.version in {path} must be a string")

    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        raise ValueError(f"tool in {path} must be a table")

    ver = tool.get("ver")
    if ver is not None:
        if not isinstance(ver, dict):
            raise ValueError(f"tool.ver in {path} must be a table")

        sha256 = ver.get("sha256")
        if sha256 is not None and not isinstance(sha256, str):
            raise ValueError(f"tool.ver.sha256 in {path} must be a string")

        exclude_patterns = ver.get("exclude_patterns")
        if exclude_patterns is not None and (
            not isinstance(exclude_patterns, list)
            or not all(isinstance(pattern, str) for pattern in exclude_patterns)
        ):
            raise ValueError(
                f"tool.ver.exclude_patterns in {path} must be an array of strings"
            )

    return Project(name=name, version=version, tool=tool)


def read_project(path: str | Path | None = None) -> Project:
    resolved = _resolve_project_path(path)
    with resolved.open("rb") as f:
        data = tomllib.load(f)
    return _project_from_data(data, resolved)


def read_head_project(path: str | Path | None = None) -> Project | None:
    resolved = _resolve_project_path(path)

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=resolved.parent,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None

    git_root = Path(os.fsdecode(completed.stdout).strip())
    try:
        git_path = resolved.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return None

    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"HEAD:{git_path}"],
            cwd=resolved.parent,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None

    completed = subprocess.run(
        ["git", "show", f"HEAD:{git_path}"],
        cwd=resolved.parent,
        check=True,
        capture_output=True,
    )
    data = tomllib.loads(os.fsdecode(completed.stdout))
    return _project_from_data(data, resolved)
