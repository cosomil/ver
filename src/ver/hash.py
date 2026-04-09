import hashlib
from pathlib import Path


def calculate_sha256(dir: str | Path) -> str:
    """
    指定されたディレクトリに含まれる以下のファイルからSHA-256ハッシュを計算する。
    - *.py
    - uv.lock
    """
    root = Path(dir)
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    files = sorted(path for path in root.rglob("*.py") if path.is_file())

    uv_lock = root / "uv.lock"
    if uv_lock.is_file():
        files.append(uv_lock)

    hasher = hashlib.sha256()
    for path in files:
        relative_path = path.relative_to(root).as_posix().encode()
        hasher.update(relative_path)
        hasher.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        hasher.update(b"\0")

    return hasher.hexdigest()
