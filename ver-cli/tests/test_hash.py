import hashlib
from pathlib import Path
import subprocess

import pytest
import ver_cli.hash as hash_module

from ver_cli.hash import HashCalculationError, calculate_sha256


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def init_git_repo(root: Path) -> None:
    root.mkdir()
    git(root, "init", "-q")


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "--all")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        message,
    )


def test_calculate_sha256_hashes_tracked_and_untracked_files(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    (root / "nested").mkdir()
    (root / "nested" / "b.txt").write_text("tracked asset\n")
    (root / "README.md").write_text("# project\n")
    (root / "ignored.txt").write_text("include me\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", "nested/b.txt", "README.md", "uv.lock")

    expected = hashlib.sha256()
    for relative_path in [
        "README.md",
        "a.py",
        "ignored.txt",
        "nested/b.txt",
        "uv.lock",
    ]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_ignores_gitignored_untracked_files(
    tmp_path: Path,
):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    (root / ".gitignore").write_text("ignored.txt\n")
    (root / "ignored.txt").write_text("ignore me\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", ".gitignore", "uv.lock")

    expected = hashlib.sha256()
    for relative_path in [".gitignore", "a.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_respects_exclude_patterns_but_keeps_uv_lock(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    (root / "assets").mkdir()
    (root / "assets" / "data.json").write_text('{"key":"value"}\n')
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", "assets/data.json", "uv.lock")

    expected = hashlib.sha256()
    expected.update(b"a.py")
    expected.update(b"\0")
    expected.update((root / "a.py").read_bytes())
    expected.update(b"\0")
    expected.update(b"uv.lock")
    expected.update(b"\0")
    expected.update((root / "uv.lock").read_bytes())
    expected.update(b"\0")

    assert calculate_sha256(root, [r"^assets/", r"^uv\.lock$"]) == expected.hexdigest()


def test_calculate_sha256_always_excludes_pyproject_toml(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    (root / "pyproject.toml").write_text('[project]\nname = "api"\nversion = "0.1.0"\n')
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", "pyproject.toml", "uv.lock")

    expected = hashlib.sha256()
    for relative_path in ["a.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_lists_files_relative_to_target_project_directory(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    init_git_repo(repo_root)

    project_a = repo_root / "packages" / "a"
    project_a.mkdir(parents=True)
    (project_a / "main.py").write_text("print('a')\n")
    (project_a / "uv.lock").write_text("lock-a\n")

    project_b = repo_root / "packages" / "b"
    project_b.mkdir(parents=True)
    (project_b / "main.py").write_text("print('b')\n")
    (project_b / "uv.lock").write_text("lock-b\n")

    git(
        repo_root,
        "add",
        "--",
        "packages/a/main.py",
        "packages/a/uv.lock",
        "packages/b/main.py",
        "packages/b/uv.lock",
    )

    expected = hashlib.sha256()
    for relative_path in ["main.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((project_a / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(project_a) == expected.hexdigest()


def test_calculate_sha256_includes_untracked_uv_lock(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py")

    expected = hashlib.sha256()
    for relative_path in ["a.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root, [r"^uv\.lock$"]) == expected.hexdigest()


def test_calculate_sha256_requires_uv_lock_in_git_ls_files_results(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / "a.py").write_text("print('a')\n")
    git(root, "add", "--", "a.py")

    with pytest.raises(HashCalculationError, match=r"uv\.lock is required") as exc_info:
        calculate_sha256(root)
    assert exc_info.value.reason == "missing_uv_lock"


def test_calculate_sha256_errors_when_uv_lock_is_gitignored(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    (root / ".gitignore").write_text("uv.lock\n")
    (root / "a.py").write_text("print('a')\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", ".gitignore", "a.py")

    with pytest.raises(
        HashCalculationError, match=r"uv\.lock must be included by git ls-files"
    ) as exc_info:
        calculate_sha256(root)
    assert exc_info.value.reason == "uv_lock_not_in_git_ls_files"


def test_calculate_sha256_uses_modified_worktree_content(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    file_path = root / "a.py"
    file_path.write_text("before\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", "uv.lock")
    file_path.write_text("after\n")

    expected = hashlib.sha256()
    for relative_path in ["a.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_skips_deleted_tracked_files(tmp_path: Path):
    root = tmp_path / "project"
    init_git_repo(root)
    deleted_file = root / "a.py"
    deleted_file.write_text("before\n")
    (root / "b.py").write_text("keep\n")
    (root / "uv.lock").write_text("lock-content\n")
    git(root, "add", "--", "a.py", "b.py", "uv.lock")
    deleted_file.unlink()

    expected = hashlib.sha256()
    for relative_path in ["b.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_hashes_submodule_using_checked_out_revision(tmp_path: Path):
    submodule_repo = tmp_path / "submodule"
    init_git_repo(submodule_repo)
    (submodule_repo / "file.txt").write_text("v1\n")
    commit_all(submodule_repo, "v1")
    revision1 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=submodule_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    (submodule_repo / "file.txt").write_text("v2\n")
    commit_all(submodule_repo, "v2")
    revision2 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=submodule_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    root = tmp_path / "project"
    init_git_repo(root)
    git(
        root,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-q",
        str(submodule_repo),
        "deps/sub",
    )
    (root / "uv.lock").write_text("lock-content\n")
    git(root / "deps" / "sub", "checkout", "-q", revision1)
    git(root, "add", "--", ".gitmodules", "deps/sub", "uv.lock")

    expected = hashlib.sha256()
    expected.update(b".gitmodules")
    expected.update(b"\0")
    expected.update((root / ".gitmodules").read_bytes())
    expected.update(b"\0")
    expected.update(b"deps/sub")
    expected.update(b"\0")
    expected.update(revision1.encode())
    expected.update(b"\0")
    expected.update(b"uv.lock")
    expected.update(b"\0")
    expected.update((root / "uv.lock").read_bytes())
    expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()

    git(root / "deps" / "sub", "checkout", "-q", revision2)

    expected = hashlib.sha256()
    expected.update(b".gitmodules")
    expected.update(b"\0")
    expected.update((root / ".gitmodules").read_bytes())
    expected.update(b"\0")
    expected.update(b"deps/sub")
    expected.update(b"\0")
    expected.update(revision2.encode())
    expected.update(b"\0")
    expected.update(b"uv.lock")
    expected.update(b"\0")
    expected.update((root / "uv.lock").read_bytes())
    expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_rejects_absolute_candidate_paths(tmp_path: Path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "uv.lock").write_text("lock-content\n")
    monkeypatch.setattr(
        hash_module, "_list_git_candidate_files", lambda _: ["/tmp/a.py", "uv.lock"]
    )

    with pytest.raises(ValueError, match=r"absolute paths are not allowed"):
        calculate_sha256(root)


def test_calculate_sha256_requires_git_worktree(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.py").write_text("print('a')\n")
    (root / "uv.lock").write_text("lock-content\n")

    with pytest.raises(
        HashCalculationError, match=r"is not inside a git worktree"
    ) as exc_info:
        calculate_sha256(root)
    assert exc_info.value.reason == "not_git_worktree"


def test_calculate_sha256_rejects_parent_traversal_candidate_paths(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "project"
    root.mkdir()
    (root / "uv.lock").write_text("lock-content\n")
    monkeypatch.setattr(
        hash_module, "_list_git_candidate_files", lambda _: ["../a.py", "uv.lock"]
    )

    with pytest.raises(ValueError, match=r"parent directory traversal is not allowed"):
        calculate_sha256(root)


def test_calculate_sha256_requires_directory(tmp_path: Path):
    file_path = tmp_path / "single.py"
    file_path.write_text("print('x')\n")

    with pytest.raises(NotADirectoryError):
        calculate_sha256(file_path)
