from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

from ver.root import find_root_dir

VER_TOML = "ver.toml"
REQUIRED_FIELDS = ("name", "version", "sha256")


@dataclass(slots=True)
class Config:
    name: str
    version: str
    sha256: str
    meta: dict[str, Any] = field(default_factory=dict)


def read_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = find_root_dir() / VER_TOML
    else:
        path = Path(path)
        if path.is_dir():
            path = path / VER_TOML
    data = toml.load(path)
    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Missing required fields in {path}: {missing}")
    return Config(
        name=data["name"],
        version=data["version"],
        sha256=data["sha256"],
        meta=data.get("meta", {}),
    )
