"""Main DeskBridge CLI entry point."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.activity_log import record_action, read_logs
from core.installer import install_wrapper
from core.loader import load_wrapper


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deskbridge")
    parser.add_argument("app", help="Application wrapper name, 'install', 'log', or 'chart'")
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

    if args.app == "log":
        limit = None
        if args.command and args.command[0].isdigit():
            limit = int(args.command[0])
        logs = read_logs(limit)
        if not logs:
            print("No activity logs found.")
            return
        for entry in logs:
            status_icon = "[OK]" if entry["status"] == "success" else "[FAILED]"
            print(f"{status_icon} {entry['timestamp']} {entry['app']} {entry['action']} {entry['message']}")
        return

    if args.app == "chart":
        from core.chart_generator import generate_chart
        output_path = generate_chart()
        print(f"[OK] Chart generated: {output_path}")
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

    # Extract action name from command args
    action_name = args.command[0] if args.command else "unknown"

    # Build args dict from remaining command line args
    action_args = {}
    remaining = args.command[1:] if len(args.command) > 1 else []
    i = 0
    while i < len(remaining):
        if remaining[i].startswith("--"):
            key = remaining[i][2:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("--"):
                action_args[key] = remaining[i + 1]
                i += 2
            else:
                action_args[key] = True
                i += 1
        else:
            i += 1

    try:
        cli_module.main(args.command)
        record_action(args.app, action_name, action_args, "success", "")
        print(f"[LOG] Action recorded: {args.app} {action_name}")
    except SystemExit as exc:
        if exc.code == 0:
            record_action(args.app, action_name, action_args, "success", "")
            print(f"[LOG] Action recorded: {args.app} {action_name}")
        else:
            record_action(args.app, action_name, action_args, "failed", f"exit code {exc.code}")
            print(f"[LOG] Action recorded (failed): {args.app} {action_name}")
        sys.exit(exc.code)


if __name__ == "__main__":
    main()