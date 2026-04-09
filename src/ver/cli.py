import argparse

from ver.config import init_config


def init(args):
    """
    ディレクトリに新しく"ver.toml"を作成します。

    Args:
        args.dir: 対象ディレクトリ。指定されていない場合、カレントディレクトリにフォールバックします
        args.name: プロジェクト名。省略した場合はディレクトリ名を使用します
        args.version: バージョン生成とSHA-256ハッシュ計算を行うかどうか。省略した場合、version は "undefined"、sha256 は空文字になります

    Raises:
        FileExistsError: すでに"ver.toml"が存在する場合に発生
    """
    config_path = init_config(args.dir, name=args.name, with_version=args.version)
    print(f"作成されました: {config_path}")


def update(_):
    print("Updating ver project...")


def check(_):
    print("Checking ver project...")


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

    s.add_parser("update").set_defaults(handler=update)

    s.add_parser("check").set_defaults(handler=check)

    args = p.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
