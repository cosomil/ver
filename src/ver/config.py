from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

from ver.calver import next_version
from ver.hash import calculate_sha256
from ver.root import find_root_dir

VER_TOML = "ver.toml"
REQUIRED_FIELDS = ("name", "version", "sha256")


@dataclass(slots=True)
class Config:
    name: str
    version: str
    sha256: str
    meta: dict[str, Any] = field(default_factory=dict)


def init_config(
    dir: str | Path | None = None,
    *,
    name: str | None = None,
    with_version: bool = False,
) -> Path:
    project_dir = Path.cwd() if dir is None else Path(dir)
    if not project_dir.is_dir():
        raise NotADirectoryError(f"{project_dir} is not a directory")

    config_path = project_dir / VER_TOML
    if config_path.exists():
        raise FileExistsError(f"{config_path} already exists")

    data = {
        "name": name or project_dir.name,
        "version": next_version() if with_version else "undefined",
        "sha256": calculate_sha256(project_dir) if with_version else "",
    }
    with config_path.open("x", encoding="utf-8") as f:
        toml.dump(data, f)

    return config_path


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
