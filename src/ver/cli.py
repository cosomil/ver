import argparse


def init(_):
    print("Initializing ver project...")


def update(_):
    print("Updating ver project...")


def check(_):
    print("Checking ver project...")


def main():
    p = argparse.ArgumentParser(prog="ver", description="A CLI tool for ver")
    s = p.add_subparsers()

    s.add_parser("init").set_defaults(handler=init)
    s.add_parser("update").set_defaults(handler=update)
    s.add_parser("check").set_defaults(handler=check)

    print("This is ver cli")
    args = p.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        p.print_help()
