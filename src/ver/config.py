from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import tomllib
from typing import Any

from ver.root import find_root_dir

VER_TOML = "ver.toml"
REQUIRED_FIELDS = ("name", "version", "sha256")


@dataclass(slots=True)
class Config:
    name: str
    version: str
    sha256: str
    exclude_patterns: list[str] = field(default_factory=list)
    no_default_exclude_patterns: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


def _resolve_config_path(path: str | Path | None = None) -> Path:
    if path is None:
        return find_root_dir() / VER_TOML

    path = Path(path)
    if path.is_dir():
        return path / VER_TOML

    return path


def _config_from_data(data: dict[str, Any], path: Path) -> Config:
    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Missing required fields in {path}: {missing}")

    exclude_patterns = data.get("exclude_patterns", [])
    if not isinstance(exclude_patterns, list) or not all(
        isinstance(pattern, str) for pattern in exclude_patterns
    ):
        raise ValueError(f"exclude_patterns in {path} must be an array of strings")

    no_default_exclude_patterns = data.get("no_default_exclude_patterns", False)
    if not isinstance(no_default_exclude_patterns, bool):
        raise ValueError(f"no_default_exclude_patterns in {path} must be a boolean")

    # metaはdictでないと
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError(f"meta in {path} must be a table")

    return Config(
        name=data["name"],
        version=data["version"],
        sha256=data["sha256"],
        exclude_patterns=exclude_patterns,
        no_default_exclude_patterns=no_default_exclude_patterns,
        meta=meta,
    )


def read_config(path: str | Path | None = None) -> Config:
    resolved = _resolve_config_path(path)
    with resolved.open("rb") as f:
        data = tomllib.load(f)
    return _config_from_data(data, resolved)


def read_head_config(path: str | Path | None = None) -> Config | None:
    resolved = _resolve_config_path(path)

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
    return _config_from_data(data, resolved)
