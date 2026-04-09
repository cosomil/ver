import hashlib
from pathlib import Path

import pytest

from ver.hash import calculate_sha256


def test_calculate_sha256_hashes_python_files_recursively_and_uv_lock(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.py").write_text("print('a')\n")
    (root / "nested").mkdir()
    (root / "nested" / "b.py").write_text("print('b')\n")
    (root / "ignored.txt").write_text("ignore me\n")
    (root / "uv.lock").write_text("lock-content\n")

    expected = hashlib.sha256()
    for relative_path in ["a.py", "nested/b.py", "uv.lock"]:
        expected.update(relative_path.encode())
        expected.update(b"\0")
        expected.update((root / relative_path).read_bytes())
        expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_ignores_non_python_files_without_uv_lock(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "a.py").write_text("print('a')\n")
    (root / "notes.md").write_text("# memo\n")

    expected = hashlib.sha256()
    expected.update(b"a.py")
    expected.update(b"\0")
    expected.update((root / "a.py").read_bytes())
    expected.update(b"\0")

    assert calculate_sha256(root) == expected.hexdigest()


def test_calculate_sha256_requires_directory(tmp_path: Path):
    file_path = tmp_path / "single.py"
    file_path.write_text("print('x')\n")

    with pytest.raises(NotADirectoryError):
        calculate_sha256(file_path)
