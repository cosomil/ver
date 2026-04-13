import pytest

from ver import Project, read_project


def test_read_project_accepts_pyproject_path(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        '[project]\nname = "example"\nversion = "2026.04.09.0"\n'
        '\n[tool.ver]\nsha256 = "abc123"\n'
    )

    project = read_project(config_path)

    assert project.name == "example"
    assert project.version == "2026.04.09.0"
    assert project.get_tool_config("ver") == {"sha256": "abc123"}


def test_read_project_reads_pyproject_from_directory(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "2026.04.09.1"\n'
    )

    project = read_project(project_dir)

    assert project.name == "example"
    assert project.version == "2026.04.09.1"


def test_read_project_reads_tool_ver_settings(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        '[project]\nname = "example"\nversion = "2026.04.09.0"\n'
        "\n[tool.ver]\n"
        'sha256 = "abc123"\n'
        'exclude_patterns = ["^dist/", "^coverage\\\\.xml$"]\n'
    )

    project = read_project(config_path)

    assert project.get_tool_config("ver") == {
        "sha256": "abc123",
        "exclude_patterns": ["^dist/", "^coverage\\.xml$"],
    }


def test_read_project_ignores_unknown_top_level_keys(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        '[project]\nname = "example"\nversion = "2026.04.09.0"\n'
        '\n[tool.foo]\nvalue = "ignored"\n'
    )

    project = read_project(config_path)

    assert project == Project(
        name="example",
        version="2026.04.09.0",
        tool={"foo": {"value": "ignored"}},
    )


def test_read_project_raises_when_project_table_is_missing(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text('[tool.ver]\nsha256 = "abc123"\n')

    with pytest.raises(ValueError, match=r"project in .* must be a table"):
        read_project(config_path)


def test_read_project_raises_when_project_version_is_missing(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text('[project]\nname = "example"\n')

    with pytest.raises(ValueError, match=r"project.version .* must be a string"):
        read_project(config_path)


def test_read_project_validates_tool_ver_exclude_patterns(tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        '[project]\nname = "example"\nversion = "2026.04.09.0"\n'
        "\n[tool.ver]\n"
        'sha256 = "abc123"\n'
        "exclude_patterns = [1]\n"
    )

    with pytest.raises(
        ValueError, match=r"tool\.ver\.exclude_patterns .* must be an array of strings"
    ):
        read_project(config_path)
