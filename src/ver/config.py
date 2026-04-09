from pathlib import Path
from typing import Any

import toml
from pydantic import BaseModel, Field

from ver.root import find_root_dir

VER_TOML = "ver.toml"


class Config(BaseModel):
    name: str
    version: str
    sha256: str
    meta: dict[str, Any] = Field(default_factory=dict)


def read_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = find_root_dir() / VER_TOML
    else:
        path = Path(path)
        if path.is_dir():
            path = path / VER_TOML
    data = toml.load(path)
    return Config(**data)
