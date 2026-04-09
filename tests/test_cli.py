import sys

import ver.config as config_module
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
    assert "Created" in capsys.readouterr().out


def test_main_init_generates_version_and_hash_with_flag(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    monkeypatch.setattr(config_module, "next_version", lambda: "2026.04.09.0")
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
