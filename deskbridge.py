"""Main DeskBridge CLI entry point."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.loader import load_wrapper


def install_wrapper(app_name: str) -> None:
    """Create a new wrapper scaffold under wrappers/<app_name>/."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wrapper_dir = os.path.join(base_dir, "wrappers", app_name)

    if os.path.exists(wrapper_dir):
        print(f"[FAILED] Wrapper '{app_name}' already exists at {wrapper_dir}")
        sys.exit(1)

    os.makedirs(wrapper_dir, exist_ok=True)

    # __init__.py
    with open(os.path.join(wrapper_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")

    # manifest.json
    manifest = {
        "name": app_name,
        "version": "0.1.0",
        "target_app": app_name.capitalize(),
        "description": f"Wrapper for controlling {app_name.capitalize()} headlessly via AI agents",
        "actions": {},
    }
    with open(os.path.join(wrapper_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # actions.py
    actions_template = '''"""Actual actions for the {app} wrapper."""

import os


def placeholder_action(input_path: str, output_path: str) -> dict:
    """Placeholder action for {app}.

    Returns a dictionary with key 'ok' (bool) and 'message' or 'error'.
    """
    if not os.path.exists(input_path):
        return {{"ok": False, "error": f"Input file not found: {{input_path}}"}}
    return {{"ok": True, "message": f"Action complete: {{output_path}}"}}
'''.format(app=app_name.capitalize())
    with open(os.path.join(wrapper_dir, "actions.py"), "w", encoding="utf-8") as f:
        f.write(actions_template)

    # cli.py
    cli_template = '''"""CLI entry point for the {app} wrapper."""

import argparse
import os
import sys

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)

from core.confirm import confirm_action
from .actions import placeholder_action


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deskbridge {app}")
    sub = parser.add_subparsers(dest="command")

    action_p = sub.add_parser("placeholder", help="Placeholder action for {app}")
    action_p.add_argument("--input", required=True, help="Path to input file")
    action_p.add_argument("--output", required=True, help="Path to output file")
    action_p.add_argument(
        "--confirm",
        action="store_true",
        help="Accept confirmation without interactive prompt (for automation)",
    )

    args = parser.parse_args(argv)

    if args.command == "placeholder":
        description = f"Placeholder {{args.input}} to {{args.output}}"
        if args.confirm or confirm_action("medium", description):
            result = placeholder_action(args.input, args.output)
            if result["ok"]:
                print(f"[OK] {{result['message']}}")
            else:
                print(f"[FAILED] {{result['error']}}")
                sys.exit(1)
        else:
            print("Cancelled by user.")
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)
'''.format(app=app_name)
    with open(os.path.join(wrapper_dir, "cli.py"), "w", encoding="utf-8") as f:
        f.write(cli_template)

    print(f"[OK] Wrapper '{app_name}' installed at wrappers/{app_name}/")
    print("Edit manifest.json, actions.py, and cli.py to define real actions.")


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
        install_wrapper(args.command[0])
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