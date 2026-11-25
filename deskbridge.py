"""Main DeskBridge CLI entry point."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.installer import install_wrapper
from core.loader import load_wrapper


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deskbridge")
    parser.add_argument("app", help="Application wrapper name or 'install' to create a new wrapper")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command and arguments for the wrapper",
    )
    args = parser.parse_args(argv)

    if args.app == "install":
        if not args.command:
            print("[FAILED] install requires an app name: deskbridge install <app_name>")
            sys.exit(1)
        result = install_wrapper(args.command[0])
        if result["ok"]:
            print(f"[OK] {result['message']}")
            print("Edit manifest.json, actions.py, and cli.py to define real actions.")
        else:
            print(f"[FAILED] {result['error']}")
            sys.exit(1)
        return

    try:
        manifest, cli_module = load_wrapper(args.app)
    except Exception as exc:
        print(f"[FAILED] Unable to load wrapper '{args.app}': {exc}")
        sys.exit(1)

    print(
        f"Wrapper: {manifest['name']} v{manifest['version']} "
        f"({manifest['target_app']})"
    )
    cli_module.main(args.command)


if __name__ == "__main__":
    main()