from ver.config import read_config


def test_read_config_accepts_ver_toml_path(tmp_path):
    config_path = tmp_path / "ver.toml"
    config_path.write_text(
        'name = "example"\nversion = "2026.04.09.0"\nsha256 = "abc123"\n'
    )

    config = read_config(config_path)

    assert config.name == "example"
    assert config.version == "2026.04.09.0"
    assert config.sha256 == "abc123"


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
