import sys
from pathlib import Path
import subprocess

import pytest
import ver.cli as cli_module
from ver.cli import main
from ver.config import read_project


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def write_pyproject(
    project_dir: Path,
    *,
    name: str = "example",
    version: str = "0.1.0",
    extra: str = "",
) -> None:
    (project_dir / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n{extra}',
        encoding="utf-8",
    )


def init_versioned_project(project_dir: Path) -> None:
    project_dir.mkdir()
    git(project_dir, "init", "-q")
    (project_dir / "main.py").write_text("print('hello')\n")
    (project_dir / "uv.lock").write_text("lock-content\n")
    write_pyproject(project_dir)
    git(project_dir, "add", "--", "main.py", "uv.lock", "pyproject.toml")


def test_main_init_updates_pyproject_for_current_directory(
    tmp_path, monkeypatch, capsys
):
    write_pyproject(tmp_path)
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "uv.lock").write_text("lock-content\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "--", "main.py", "uv.lock", "pyproject.toml")
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ver", "init"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    project = read_project(tmp_path / "pyproject.toml")
    ver = project.get_tool_config("ver")
    assert exc_info.value.code == 0
    assert project.name == tmp_path.name
    assert project.version == "2026.04.09.0"
    assert ver is not None
    assert ver["sha256"]
    assert ver["exclude_patterns"] == list(cli_module.DEFAULT_EXCLUDE_PATTERNS)
    assert (
        capsys.readouterr().out == "初期化されました\n"
        'version = "2026.04.09.0"\n'
        f'sha256 = "{ver["sha256"]}"\n'
    )


def test_main_init_generates_version_and_hash(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(
        sys,
        "argv",
        ["ver", "init", str(project_dir), "--name", "api"],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    project = read_project(project_dir / "pyproject.toml")
    ver = project.get_tool_config("ver")
    assert exc_info.value.code == 0
    assert project.name == "api"
    assert project.version == "2026.04.09.0"
    assert isinstance(ver, dict)
    assert ver["sha256"]
    assert ver["exclude_patterns"] == list(cli_module.DEFAULT_EXCLUDE_PATTERNS)
    assert exc_info.value.code == 0


def test_main_init_writes_default_exclude_patterns_as_literal_strings(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(sys, "argv", ["ver", "init", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    text = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert exc_info.value.code == 0
    assert "exclude_patterns = [\n" in text
    assert "    '^\\.[^/]+$',\n" in text
    assert "    '^tests/',\n" in text
    assert "    '^(README\\.md|AGENTS\\.md|CLAUDE\\.md)$',\n" in text
    assert "    '^LICENSE\\.(txt|md|rst)$',\n" in text


def test_main_init_requires_pyproject_toml(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    monkeypatch.setattr(sys, "argv", ["ver", "init", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert '先に "uv init" を実行してください' in capsys.readouterr().err


def test_main_init_fails_outside_git_worktree(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")
    (project_dir / "uv.lock").write_text("lock-content\n")
    write_pyproject(project_dir)
    monkeypatch.setattr(cli_module, "next_version", lambda: "2026.04.09.0")
    monkeypatch.setattr(sys, "argv", ["ver", "init", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "gitで管理されていないディレクトリ" in capsys.readouterr().err


def test_main_update_updates_existing_pyproject(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    write_pyproject(
        project_dir,
        name="api",
        version="2026.04.09.0",
        extra='\n[tool.ver]\nsha256 = "old"\nexclude_patterns = []\n',
    )
    calls = []

    def fake_next_version(current_ver=None):
        calls.append(current_ver)
        return "2026.04.09.1"

    monkeypatch.setattr(cli_module, "next_version", fake_next_version)
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    project = read_project(project_dir / "pyproject.toml")
    ver = project.get_tool_config("ver")
    assert exc_info.value.code == 0
    assert calls == [None]
    assert project.version == "2026.04.09.1"
    assert ver is not None
    assert ver["sha256"] != "old"
    assert (
        capsys.readouterr().out == "更新されました\n"
        f'version = "{project.version}"\n'
        f'sha256 = "{ver["sha256"]}"\n'
    )


def test_main_update_preserves_comments_and_unrelated_tool_tables(
    tmp_path, monkeypatch
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    config_path = project_dir / "pyproject.toml"
    config_path.write_text(
        "# user comment\n"
        "[project]\n"
        'name = "api"\n'
        'version = "2026.04.09.0" # version comment\n'
        "\n"
        "[tool.ver]\n"
        "# keep this comment\n"
        'sha256 = "old"\n'
        "exclude_patterns = []\n"
        "\n"
        "[tool.foo]\n"
        'owner = "user"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_module, "next_version", lambda current_ver=None: "2026.04.09.1"
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    updated = config_path.read_text(encoding="utf-8")
    assert exc_info.value.code == 0
    assert "# user comment" in updated
    assert "# version comment" in updated
    assert "# keep this comment" in updated
    assert "[tool.foo]" in updated
    assert 'owner = "user"' in updated


def test_main_update_accepts_out_of_order_tool_table_proxy(tmp_path, monkeypatch):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    config_path = project_dir / "pyproject.toml"
    config_path.write_text(
        "[project]\n"
        'name = "api"\n'
        'version = "2026.04.09.0"\n'
        "\n"
        "[tool.foo]\n"
        'owner = "user"\n'
        "\n"
        "[tool.ver]\n"
        'sha256 = "old"\n'
        "exclude_patterns = []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_module, "next_version", lambda current_ver=None: "2026.04.09.1"
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    project = read_project(config_path)
    ver = project.get_tool_config("ver")
    assert exc_info.value.code == 0
    assert project.version == "2026.04.09.1"
    assert ver is not None
    assert ver["sha256"] != "old"


def test_main_update_exits_without_changes_when_sha256_is_unchanged(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    sha256 = cli_module.calculate_sha256(project_dir, [])
    config_path = project_dir / "pyproject.toml"
    original = (
        '[project]\nname = "api"\nversion = "2026.04.09.0"\n'
        "\n[tool.ver]\n"
        f'sha256 = "{sha256}"\n'
        "exclude_patterns = []\n"
    )
    config_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(
        cli_module,
        "next_version",
        lambda current_ver: pytest.fail("next_version should not be called"),
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert config_path.read_text(encoding="utf-8") == original
    assert (
        capsys.readouterr().out == "更新はありません\n"
        f'version = "2026.04.09.0"\n'
        f'sha256 = "{sha256}"\n'
    )


def test_main_update_uses_head_version_when_pyproject_has_uncommitted_changes(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    config_path = project_dir / "pyproject.toml"
    head_sha256 = cli_module.calculate_sha256(project_dir, [])
    config_path.write_text(
        '[project]\nname = "api"\nversion = "2026.04.09.0"\n'
        "\n[tool.ver]\n"
        f'sha256 = "{head_sha256}"\n'
        "exclude_patterns = []\n",
        encoding="utf-8",
    )
    git(project_dir, "add", "--", "pyproject.toml")
    git(
        project_dir,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "initial version",
    )

    (project_dir / "main.py").write_text("print('hello v2')\n")
    stale_sha256 = cli_module.calculate_sha256(project_dir, [])
    config_path.write_text(
        '[project]\nname = "api"\nversion = "2026.04.09.1"\n'
        "\n[tool.ver]\n"
        f'sha256 = "{stale_sha256}"\n'
        "exclude_patterns = []\n",
        encoding="utf-8",
    )
    (project_dir / "main.py").write_text("print('hello v3')\n")

    def fake_next_version(current_ver):
        assert current_ver == "2026.04.09.0"
        return "2026.04.09.1"

    monkeypatch.setattr(cli_module, "next_version", fake_next_version)
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    expected_sha256 = cli_module.calculate_sha256(project_dir, [])
    project = read_project(config_path)
    ver = project.get_tool_config("ver")
    assert exc_info.value.code == 0
    assert project.version == "2026.04.09.1"
    assert ver is not None
    assert ver["sha256"] == expected_sha256
    assert (
        capsys.readouterr().out == "更新されました\n"
        'version = "2026.04.09.1"\n'
        f'sha256 = "{expected_sha256}"\n'
    )


def test_main_update_prompts_init_when_tool_ver_is_missing(
    tmp_path, monkeypatch, capsys
):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    write_pyproject(
        project_dir,
        name="api",
        version="2026.04.09.0",
    )
    monkeypatch.setattr(sys, "argv", ["ver", "update", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert (
        capsys.readouterr().err
        == 'エラー: "tool.ver" が設定されていません。先に "ver init" を実行してください\n'
    )


def test_main_check_succeeds_when_sha256_is_unchanged(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    sha256 = cli_module.calculate_sha256(project_dir, [])
    write_pyproject(
        project_dir,
        name="api",
        version="2026.04.09.0",
        extra=f'\n[tool.ver]\nsha256 = "{sha256}"\nexclude_patterns = []\n',
    )
    monkeypatch.setattr(sys, "argv", ["ver", "check", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f'version = "2026.04.09.0"\nsha256 = "{sha256}"\n'


def test_main_check_fails_when_sha256_differs(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    write_pyproject(
        project_dir,
        name="api",
        version="2026.04.09.0",
        extra='\n[tool.ver]\nsha256 = "old"\nexclude_patterns = []\n',
    )
    monkeypatch.setattr(sys, "argv", ["ver", "check", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    recalculated_sha256 = cli_module.calculate_sha256(project_dir, [])
    assert (
        capsys.readouterr().err == "エラー: 整合していません\n"
        'version = "2026.04.09.0"\n'
        'sha256 = "old"\n'
        f'actual_sha256 = "{recalculated_sha256}"\n'
    )


def test_main_check_respects_configured_exclude_patterns(tmp_path, monkeypatch, capsys):
    project_dir = tmp_path / "service"
    init_versioned_project(project_dir)
    (project_dir / "generated.txt").write_text("ignore me\n")
    git(project_dir, "add", "--", "generated.txt")
    sha256 = cli_module.calculate_sha256(project_dir, [r"^generated\.txt$"])
    write_pyproject(
        project_dir,
        name="api",
        version="2026.04.09.0",
        extra=(
            "\n[tool.ver]\n"
            f'sha256 = "{sha256}"\n'
            'exclude_patterns = ["^generated\\\\.txt$"]\n'
        ),
    )
    monkeypatch.setattr(sys, "argv", ["ver", "check", str(project_dir)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f'version = "2026.04.09.0"\nsha256 = "{sha256}"\n'
