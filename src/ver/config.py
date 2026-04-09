from dataclasses import dataclass, field
from pathlib import Path
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


def read_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = find_root_dir() / VER_TOML
    else:
        path = Path(path)
        if path.is_dir():
            path = path / VER_TOML
    with path.open("rb") as f:
        data = tomllib.load(f)
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
