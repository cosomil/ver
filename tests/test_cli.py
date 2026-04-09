import sys
from pathlib import Path
import subprocess

import pytest
import ver.cli as cli_module
from ver.cli import main
from ver.config import read_config


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def init_versioned_project(project_dir: Path) -> None:
    project_dir.mkdir()
    git(project_dir, "init", "-q")
    (project_dir / "main.py").write_text("print('hello')\n")
    (project_dir / "uv.lock").write_text("lock-content\n")
    git(project_dir, "add", "--", "main.py", "uv.lock")


def test_main_init_creates_ver_toml_for_current_directory(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ver", "init"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    config = read_config(tmp_path / "ver.toml")
    assert exc_info.value.code == 0
    assert config.name == tmp_path.name
    assert config.version == "undefined"
    assert config.sha256 == ""
    assert "作成されました" in capsys.readouterr().out


def test_main_init_generates_version_and_hash_with_flag(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(
        sys,
        "argv",
        ["ver", "init", str(project_dir), "--name", "api", "--version"],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    config = read_config(project_dir / "ver.toml")
    assert exc_info.value.code == 0
    assert config.name == "api"
    assert config.version == "2026.04.09.0"
    assert config.sha256


def test_main_init_with_version_fails_outside_git_worktree(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    (project_dir / "uv.lock").write_text("lock-content\n")
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(sys, "argv", ["ver", "init", str(project_dir), "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "is not inside a git worktree" in capsys.readouterr().err


def test_main_update_updates_existing_ver_toml(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    (project_dir / "ver.toml").write_text(
        'name = "api"\nversion = "2026.04.09.0"\nsha256 = "old"\n'
    )
    monkeypatch.setattr(cli_module, "next_version", lambda current_ver: "2026.04.09.1")
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    config = read_config(project_dir / "ver.toml")
    assert exc_info.value.code == 0
    assert config.version == "2026.04.09.1"
    assert config.sha256 != "old"
    assert (
        capsys.readouterr().out == "更新されました\n"
        f'version = "{config.version}"\n'
        f'sha256 = "{config.sha256}"\n'
    )


def test_main_update_preserves_comments_and_meta_table(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    config_path = project_dir / "ver.toml"
    config_path.write_text(
        "# user comment\n"
        'name = "api"\n'
        'version = "2026.04.09.0" # version comment\n'
        'sha256 = "old"\n'
        "\n"
        "[meta]\n"
        "# keep this comment\n"
        'owner = "user"\n'
    )
    monkeypatch.setattr(cli_module, "next_version", lambda current_ver: "2026.04.09.1")
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    updated = config_path.read_text()
    assert exc_info.value.code == 0
    assert "# user comment" in updated
    assert "# version comment" in updated
    assert "[meta]" in updated
    assert "# keep this comment" in updated
    assert 'owner = "user"' in updated


def test_main_update_exits_without_changes_when_sha256_is_unchanged(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    sha256 = cli_module.calculate_sha256(project_dir)
    config_path = project_dir / "ver.toml"
    original = f'name = "api"\nversion = "2026.04.09.0"\nsha256 = "{sha256}"\n'
    config_path.write_text(original)
    monkeypatch.setattr(
        cli_module,
        "next_version",
        lambda current_ver: pytest.fail("next_version should not be called"),
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert config_path.read_text() == original
    assert (
        capsys.readouterr().out == "更新はありません\n"
        f'version = "2026.04.09.0"\n'
        f'sha256 = "{sha256}"\n'
    )


def test_main_check_succeeds_when_sha256_is_unchanged(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    sha256 = cli_module.calculate_sha256(project_dir)
    (project_dir / "ver.toml").write_text(
        f'name = "api"\nversion = "2026.04.09.0"\nsha256 = "{sha256}"\n'
    )
    monkeypatch.setattr(sys, "argv", ["ver", "check", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f'version = "2026.04.09.0"\nsha256 = "{sha256}"\n'


def test_main_check_fails_when_sha256_differs(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    (project_dir / "ver.toml").write_text(
        'name = "api"\nversion = "2026.04.09.0"\nsha256 = "old"\n'
    )
    monkeypatch.setattr(sys, "argv", ["ver", "check", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    recalculated_sha256 = cli_module.calculate_sha256(project_dir)
    assert (
        capsys.readouterr().err == "エラー: 整合していません\n"
        'version = "2026.04.09.0"\n'
        'sha256 = "old"\n'
        f'actual_sha256 = "{recalculated_sha256}"\n'
    )
