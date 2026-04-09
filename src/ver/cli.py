import argparse
from pathlib import Path
import sys

import toml

from ver.calver import next_version
from ver.config import VER_TOML, read_config
from ver.hash import calculate_sha256


def exit(message: str, code: int = 1):
    print(message, file=sys.stdout if code == 0 else sys.stderr)
    sys.exit(code)


def init(args):
    """
    ディレクトリに新しく"ver.toml"を作成します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
        args.name: プロジェクト名。省略した場合はディレクトリ名を使用します
        args.version: バージョン生成とSHA-256ハッシュ計算を行うかどうか。省略した場合、version は "undefined"、sha256 は空文字になります
    """
    try:
        project_dir = Path.cwd() if args.dir is None else Path(args.dir)
        if not project_dir.is_dir():
            raise NotADirectoryError(f"{project_dir} is not a directory")

        config_path = project_dir / VER_TOML
        data = {
            "name": args.name or project_dir.name,
            "version": next_version() if args.version else "undefined",
            "sha256": calculate_sha256(project_dir) if args.version else "",
        }
        with config_path.open("x", encoding="utf-8") as f:
            toml.dump(data, f)
        exit(f"作成されました: {config_path}", code=0)
    except FileExistsError:
        exit('エラー: "ver.toml"が既に存在しています', code=1)
    except Exception as e:
        exit(f"エラーが発生しました: {e}", code=1)


def update(args):
    """
    "ver.toml"のversionを更新し、sha256を再計算します。
    ただし、sha256に変更がない場合は更新せずに終了します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
    """
    try:
        project_dir = Path.cwd() if args.dir is None else Path(args.dir)
        if not project_dir.is_dir():
            raise NotADirectoryError(f"{project_dir} is not a directory")

        config_path = project_dir / VER_TOML
        config = read_config(config_path)
        current_sha256 = calculate_sha256(project_dir)
        if config.sha256 == current_sha256:
            exit(
                "更新はありません\n"
                f'version = "{config.version}"\n'
                f'sha256 = "{config.sha256}"',
                code=0,
            )
        else:
            data = toml.load(config_path)
            data["version"] = next_version(config.version)
            data["sha256"] = current_sha256
            with config_path.open("w", encoding="utf-8") as f:
                toml.dump(data, f)
            exit(
                "更新されました\n"
                f'version = "{data["version"]}"\n'
                f'sha256 = "{data["sha256"]}"',
                code=0,
            )
    except FileNotFoundError:
        exit('エラー: "ver.toml"が見つかりません', code=1)
    except Exception as e:
        exit(f"エラーが発生しました: {e}", code=1)


def check(args):
    """
    "ver.toml"のversionとsha256が現在の状態と一致するかを確認します。
    一致する場合は正常終了し、一致しない場合はエラー終了します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
    """
    try:
        project_dir = Path.cwd() if args.dir is None else Path(args.dir)
        if not project_dir.is_dir():
            raise NotADirectoryError(f"{project_dir} is not a directory")

        config_path = project_dir / VER_TOML
        config = read_config(config_path)
        current_sha256 = calculate_sha256(project_dir)
        if config.sha256 == current_sha256:
            exit(
                f'version = "{config.version}"\nsha256 = "{config.sha256}"',
                code=0,
            )
        else:
            exit(
                "エラー: 整合していません\n"
                f'version = "{config.version}"\n'
                f'sha256 = "{config.sha256}"\n'
                f'actual_sha256 = "{current_sha256}"',
                code=1,
            )
    except FileNotFoundError:
        exit('エラー: "ver.toml"が見つかりません', code=1)
    except Exception as e:
        exit(f"エラーが発生しました: {e}", code=1)


def main():
    p = argparse.ArgumentParser(prog="ver", description="A CLI tool for ver")
    s = p.add_subparsers()

    # ver init [dir] --name NAME --version
    init_parser = s.add_parser(
        "init", help='ディレクトリに新しく"ver.toml"を作成します'
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
    init_parser.add_argument(
        "--version",
        action="store_true",
        help='バージョン生成とSHA-256ハッシュ計算を行うかどうか。省略した場合、version は "undefined"、sha256 は空文字になります',
    )
    init_parser.set_defaults(handler=init)

    update_parser = s.add_parser(
        "update", help='"ver.toml"のversionを更新し、sha256を再計算します'
    )
    update_parser.add_argument(
        "dir",
        nargs="?",
        default=None,
        help="対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします",
    )
    update_parser.set_defaults(handler=update)

    check_parser = s.add_parser(
        "check", help='"ver.toml"のversionとsha256が現在の状態と一致するかを確認します'
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
