import pytest

import ver.config as config_module
from ver.config import Config, init_config, read_config


def test_read_config_accepts_ver_toml_path(tmp_path):
    config_path = tmp_path / "ver.toml"
    config_path.write_text(
        'name = "example"\nversion = "2026.04.09.0"\nsha256 = "abc123"\n'
    )

    config = read_config(config_path)

    assert config.name == "example"
    assert config.version == "2026.04.09.0"
    assert config.sha256 == "abc123"
    assert config.meta == {}


def test_read_config_reads_ver_toml_from_directory(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "ver.toml").write_text(
        'name = "example"\nversion = "2026.04.09.1"\nsha256 = "def456"\n'
    )

    config = read_config(project_dir)

    assert config.name == "example"
    assert config.version == "2026.04.09.1"
    assert config.sha256 == "def456"


def test_read_config_ignores_unknown_top_level_keys(tmp_path):
    config_path = tmp_path / "ver.toml"
    config_path.write_text(
        'name = "example"\n'
        'version = "2026.04.09.0"\n'
        'sha256 = "abc123"\n'
        'extra = "ignored"\n'
    )

    config = read_config(config_path)

    assert config == Config(name="example", version="2026.04.09.0", sha256="abc123")


def test_read_config_raises_when_required_field_is_missing(tmp_path):
    config_path = tmp_path / "ver.toml"
    config_path.write_text('name = "example"\nversion = "2026.04.09.0"\n')

    with pytest.raises(ValueError, match=r"Missing required fields .*: sha256"):
        read_config(config_path)


def test_read_config_reports_multiple_missing_required_fields(tmp_path):
    config_path = tmp_path / "ver.toml"
    config_path.write_text('name = "example"\n')

    with pytest.raises(
        ValueError, match=r"Missing required fields .*: version, sha256"
    ):
        read_config(config_path)


def test_init_config_creates_ver_toml_with_defaults(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")

    config_path = init_config(project_dir)

    assert config_path == project_dir / "ver.toml"
    config = read_config(config_path)
    assert config.name == "project"
    assert config.version == "undefined"
    assert config.sha256 == ""


def test_init_config_generates_version_and_hash_when_enabled(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    monkeypatch.setattr(config_module, "next_version", lambda: "2026.04.09.0")

    config_path = init_config(project_dir, name="custom-name", with_version=True)

    config = read_config(config_path)
    assert config.name == "custom-name"
    assert config.version == "2026.04.09.0"
    assert config.sha256


def test_init_config_raises_when_ver_toml_already_exists(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "ver.toml").write_text('name = "example"\n')

    with pytest.raises(FileExistsError):
        init_config(project_dir)
