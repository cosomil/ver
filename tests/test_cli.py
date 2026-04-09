import sys

import pytest
import ver.cli as cli_module
from ver.cli import main
from ver.config import read_config


def test_main_init_creates_ver_toml_for_current_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ver", "init"])

    main()

    config = read_config(tmp_path / "ver.toml")
    assert config.name == tmp_path.name
    assert config.version == "undefined"
    assert config.sha256 == ""
    assert "作成されました" in capsys.readouterr().out


def test_main_init_generates_version_and_hash_with_flag(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(
        sys,
        "argv",
        ["ver", "init", str(project_dir), "--name", "api", "--version"],
    )

    main()

    config = read_config(project_dir / "ver.toml")
    assert config.name == "api"
    assert config.version == "2026.04.09.0"
    assert config.sha256


def test_main_update_updates_existing_ver_toml(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    (project_dir / "ver.toml").write_text(
        'name = "api"\nversion = "2026.04.09.0"\nsha256 = "old"\n'
    )
    monkeypatch.setattr(cli_module, "next_version", lambda current_ver: "2026.04.09.1")
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    main()

    config = read_config(project_dir / "ver.toml")
    assert config.version == "2026.04.09.1"
    assert config.sha256 != "old"
    assert "更新されました" in capsys.readouterr().out


def test_main_update_exits_without_changes_when_sha256_is_unchanged(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    sha256 = cli_module.calculate_sha256(project_dir)
    config_path = project_dir / "ver.toml"
    original = (
        'name = "api"\n'
        'version = "2026.04.09.0"\n'
        f'sha256 = "{sha256}"\n'
    )
    config_path.write_text(original)
    monkeypatch.setattr(
        cli_module,
        "next_version",
        lambda current_ver: pytest.fail("next_version should not be called"),
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    main()

    assert config_path.read_text() == original
    assert "更新はありません" in capsys.readouterr().out
