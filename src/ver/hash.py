import os
import hashlib
import posixpath
from pathlib import Path
import re
import subprocess
from typing import Literal, Pattern, Sequence, assert_never

from ver.config import VER_TOML


HashCalculationErrorReason = Literal[
    "not_git_worktree",
    "missing_uv_lock",
    "uv_lock_not_in_git_ls_files",
]


class HashCalculationError(RuntimeError):
    reason: HashCalculationErrorReason
    root: Path

    def __init__(self, reason: HashCalculationErrorReason, root: Path):
        self._reason = reason
        self.root = root
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        match self.reason:
            case "not_git_worktree":
                return f"{self.root} is not inside a git worktree"
            case "missing_uv_lock":
                return f"uv.lock is required in {self.root}"
            case "uv_lock_not_in_git_ls_files":
                return f"uv.lock must be included by git ls-files in {self.root}"

        assert_never(self.reason)  # pyright: ignore[reportUnreachable]


def _normalize_posix_path(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if normalized.startswith("./"):
        normalized = normalized[2:]

    if posixpath.isabs(normalized):
        raise ValueError(f"absolute paths are not allowed: {path}")

    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"parent directory traversal is not allowed: {path}")

    return normalized


def _list_git_candidate_files(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--modified",
                "--others",
                "--exclude-standard",
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = os.fsdecode(exc.stderr).strip()
        if "not a git repository" in stderr.lower():
            raise HashCalculationError("not_git_worktree", root) from exc
        raise RuntimeError(stderr or f"git ls-files failed in {root}") from exc

    files = {
        _normalize_posix_path(os.fsdecode(raw_path))
        for raw_path in completed.stdout.split(b"\0")
        if raw_path
    }
    return sorted(files)


def calculate_sha256(
    dir: str | Path, exclude_patterns: Sequence[str] | None = None
) -> str:
    """
    指定されたディレクトリ配下のgit管理ファイルと未追跡ファイルからSHA-256ハッシュを計算する。
    ver.toml は常に除外し、uv.lock は除外パターンでは除外しない。
    """
    root = Path(dir)
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    uv_lock_path = root / "uv.lock"
    if not uv_lock_path.is_file():
        raise HashCalculationError("missing_uv_lock", root)

    candidate_files = _list_git_candidate_files(root)
    if "uv.lock" not in candidate_files:
        raise HashCalculationError("uv_lock_not_in_git_ls_files", root)

    compiled_patterns: list[Pattern[str]] = [
        re.compile(pattern) for pattern in exclude_patterns or []
    ]
    files: list[tuple[str, Path]] = []
    for relative_path in candidate_files:
        relative_path = _normalize_posix_path(relative_path)
        if relative_path == VER_TOML:
            continue

        if relative_path != "uv.lock" and any(
            pattern.search(relative_path) for pattern in compiled_patterns
        ):
            continue

        path = root.joinpath(*relative_path.split("/"))
        if not path.is_file():
            continue
        files.append((relative_path, path))

    hasher = hashlib.sha256()
    for relative_path, path in files:
        hasher.update(relative_path.encode())
        hasher.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        hasher.update(b"\0")

    return hasher.hexdigest()
