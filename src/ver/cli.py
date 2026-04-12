import argparse
from pathlib import Path
import sys
from typing import Union

import tomlkit
from tomlkit.items import Table
from tomlkit.container import OutOfOrderTableProxy

from ver.calver import next_version
from ver.config import PYPROJECT_TOML, Project, read_head_project, read_project
from ver.hash import HashCalculationError, calculate_sha256


DEFAULT_EXCLUDE_PATTERNS = (
    r"^\.[^/]+$",
    r"^tests/",
    r"^(README\.md|AGENTS\.md|CLAUDE\.md)$",
    r"^LICENSE\.(txt|md|rst)$",
)


TableLike = Union[Table, OutOfOrderTableProxy]


def resolve_exclude_patterns(project: Project) -> tuple[str, ...]:
    ver = project.get_tool_config("ver") or {}
    exclude_patterns = ver.get("exclude_patterns", [])
    if not isinstance(exclude_patterns, list) or not all(
        isinstance(pattern, str) for pattern in exclude_patterns
    ):
        raise ValueError("tool.ver.exclude_patterns must be an array of strings")
    return tuple(exclude_patterns)


def exit(message: str, code: int = 1):
    print(message, file=sys.stdout if code == 0 else sys.stderr)
    return SystemExit(code)


def _resolve_project_dir(dir: str | None) -> Path:
    project_dir = Path.cwd() if dir is None else Path(dir)
    if not project_dir.is_dir():
        raise NotADirectoryError(f"{project_dir} is not a directory")
    return project_dir


def _load_pyproject_document(project_dir: Path) -> tuple[Path, tomlkit.TOMLDocument]:
    pyproject_path = project_dir / PYPROJECT_TOML
    if not pyproject_path.is_file():
        raise FileNotFoundError(pyproject_path)
    return pyproject_path, tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))


def _require_table(parent: tomlkit.TOMLDocument | TableLike, key: str) -> TableLike:
    value = parent.get(key)
    if value is None:
        value = tomlkit.table()
        parent[key] = value
    if not isinstance(value, (Table, OutOfOrderTableProxy)):
        raise ValueError(f"{key} must be a table")
    return value


def _get_project_sha256(project: Project) -> str:
    ver = project.get_tool_config("ver")
    if ver is None:
        raise ValueError("tool.ver が設定されていません")

    sha256 = ver.get("sha256")
    if not isinstance(sha256, str):
        raise ValueError("tool.ver.sha256 が文字列で設定されていません")
    return sha256


def _prepare_pyproject(
    doc: tomlkit.TOMLDocument, *, name: str, version: str, sha256: str
) -> tomlkit.TOMLDocument:
    project = _require_table(doc, "project")
    tool = _require_table(doc, "tool")
    ver = _require_table(tool, "ver")

    project["name"] = name
    project["version"] = version
    ver["sha256"] = sha256
    patterns = tomlkit.array()
    patterns.multiline(True)
    [
        patterns.add_line(tomlkit.string(p, literal=True))
        for p in DEFAULT_EXCLUDE_PATTERNS
    ]
    ver["exclude_patterns"] = patterns

    return doc


def init(args):
    """
    pyproject.toml に ver 用の設定を書き込みます。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
        args.name: プロジェクト名。省略した場合はディレクトリ名を使用します
    """
    try:
        project_dir = _resolve_project_dir(args.dir)
        pyproject_path, doc = _load_pyproject_document(project_dir)
        version = next_version()
        sha256 = calculate_sha256(project_dir, DEFAULT_EXCLUDE_PATTERNS)
        _prepare_pyproject(
            doc,
            name=args.name or project_dir.name,
            version=version,
            sha256=sha256,
        )
        pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        raise exit(
            f'初期化されました\nversion = "{version}"\nsha256 = "{sha256}"',
            code=0,
        )
    except FileNotFoundError:
        raise exit(
            'エラー: "pyproject.toml"が見つかりません。先に "uv init" を実行してください',
            code=1,
        )
    except HashCalculationError as e:
        match e.reason:
            case "missing_uv_lock":
                raise exit("エラー: uv.lock が見つかりません", code=1)
            case "not_git_worktree":
                raise exit(
                    f"エラー: gitで管理されていないディレクトリのハッシュ値を計算することができません: {e.root}",
                    code=1,
                )
            case "uv_lock_not_in_git_ls_files":
                raise exit(
                    f'エラー: "uv.lock"がgitで管理されていないためハッシュ値を計算することができません: {e.root}',
                    code=1,
                )
    except Exception as e:
        raise exit(f"エラーが発生しました: {e}", code=1)


def update(args):
    """
    pyproject.toml の version を更新し、sha256 を再計算します。
    ただし、sha256 に変更がない場合は更新せずに終了します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
    """
    try:
        project_dir = _resolve_project_dir(args.dir)
        pyproject_path = project_dir / PYPROJECT_TOML
        project = read_project(pyproject_path)
    except FileNotFoundError:
        raise exit(
            'エラー: "pyproject.toml"が見つかりません。先に "uv init" を実行してください',
            code=1,
        )
    except Exception as e:
        raise exit(f"エラーが発生しました: {e}", code=1)

    try:
        current_sha256 = calculate_sha256(
            project_dir, resolve_exclude_patterns(project)
        )
        recorded_sha256 = _get_project_sha256(project)
        if recorded_sha256 == current_sha256:
            raise exit(
                "更新はありません\n"
                f'version = "{project.version}"\n'
                f'sha256 = "{recorded_sha256}"',
                code=0,
            )

        head_project = read_head_project(pyproject_path)
        base_version = None if head_project is None else head_project.version
        _, doc = _load_pyproject_document(project_dir)
        project_table = _require_table(doc, "project")
        ver_table = _require_table(_require_table(doc, "tool"), "ver")
        new_version = next_version(base_version)
        project_table["version"] = new_version
        ver_table["sha256"] = current_sha256
        pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        raise exit(
            f'更新されました\nversion = "{new_version}"\nsha256 = "{current_sha256}"',
            code=0,
        )
    except HashCalculationError as e:
        match e.reason:
            case "missing_uv_lock":
                raise exit("エラー: uv.lock が見つかりません", code=1)
            case "not_git_worktree":
                raise exit(
                    f"エラー: gitで管理されていないディレクトリのハッシュ値を計算することができません: {e.root}",
                    code=1,
                )
            case "uv_lock_not_in_git_ls_files":
                raise exit(
                    f'エラー: "uv.lock"がgitで管理されていないためハッシュ値を計算することができません: {e.root}',
                    code=1,
                )
    except Exception as e:
        raise exit(f"エラーが発生しました: {e}", code=1)


def check(args):
    """
    pyproject.toml の version と sha256 が現在の状態と一致するかを確認します。
    一致する場合は正常終了し、一致しない場合はエラー終了します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
    """
    try:
        project_dir = _resolve_project_dir(args.dir)
        pyproject_path = project_dir / PYPROJECT_TOML
        project = read_project(pyproject_path)
        recorded_sha256 = _get_project_sha256(project)
        current_sha256 = calculate_sha256(
            project_dir, resolve_exclude_patterns(project)
        )
        if recorded_sha256 == current_sha256:
            raise exit(
                f'version = "{project.version}"\nsha256 = "{recorded_sha256}"',
                code=0,
            )
        raise exit(
            "エラー: 整合していません\n"
            f'version = "{project.version}"\n'
            f'sha256 = "{recorded_sha256}"\n'
            f'actual_sha256 = "{current_sha256}"',
            code=1,
        )
    except FileNotFoundError:
        raise exit(
            'エラー: "pyproject.toml"が見つかりません。先に "uv init" を実行してください',
            code=1,
        )
    except Exception as e:
        raise exit(f"エラーが発生しました: {e}", code=1)


def main():
    p = argparse.ArgumentParser(
        prog="ver",
        description="プロジェクトのバージョンの管理、検査を行います。\n"
        "対象のプロジェクトはuvで作成され、gitで管理されている必要があります",
    )
    s = p.add_subparsers()

    init_parser = s.add_parser(
        "init", help="pyproject.toml に ver 用の設定を書き込みます"
    )
    init_parser.add_argument(
        "dir",
        nargs="?",
        default=None,
        help="対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします",
    )
    init_parser.add_argument(
        "--name", help="プロジェクト名。省略した場合はディレクトリ名を使用します"
    )
    init_parser.set_defaults(handler=init)

    update_parser = s.add_parser(
        "update", help="pyproject.toml の version を更新し、sha256 を再計算します"
    )
    update_parser.add_argument(
        "dir",
        nargs="?",
        default=None,
        help="対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします",
    )
    update_parser.set_defaults(handler=update)

    check_parser = s.add_parser(
        "check",
        help="pyproject.toml の version と sha256 が現在の状態と一致するかを確認します",
    )
    check_parser.add_argument(
        "dir",
        nargs="?",
        default=None,
        help="対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします",
    )
    check_parser.set_defaults(handler=check)

    args = p.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
