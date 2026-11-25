"""Main DeskBridge CLI entry point."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.activity_log import record_action, read_logs
from core.chart_generator import generate_chart
from core.desktop_control import (
    capture, click, type_text, press_keys, scroll, drag,
    list_apps, list_windows, focus_app,
)
from core.installer import install_wrapper
from core.loader import load_wrapper


DESKTOP_RISKY_ACTIONS = {"click", "type", "key", "drag"}


def _desktop_confirm(action: str, target: str) -> bool:
    """Ask user confirmation for risky desktop actions."""
    answer = input(f"[DESKBRIDGE] Confirm desktop action [{action}] on {target}? (y/n): ")
    return answer.strip().lower() == "y"


def _handle_desktop(argv: list) -> int:
    """Handle `deskbridge desktop <action> [options]` subcommand."""
    parser = argparse.ArgumentParser(prog="deskbridge desktop")
    sub = parser.add_subparsers(dest="desktop_action")

    # capture
    cap = sub.add_parser("capture", help="Capture screenshot")
    cap.add_argument("--app", help="Target application name")
    cap.add_argument("--mode", default="som", choices=["som", "vision", "ax"], help="Capture mode")

    # click
    clk = sub.add_parser("click", help="Click an element")
    clk.add_argument("--element", type=int, help="SOM element index (1-based)")
    clk.add_argument("--coordinate", nargs=2, type=int, metavar=("X", "Y"), help="Pixel coordinates")
    clk.add_argument("--app", help="Target application name")
    clk.add_argument("--button", default="left", choices=["left", "right", "middle"])
    clk.add_argument("--delivery-mode", default="background", choices=["background", "foreground"])
    clk.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    # type
    typ = sub.add_parser("type", help="Type text")
    typ.add_argument("text", help="Text to type")
    typ.add_argument("--app", help="Target application name")
    typ.add_argument("--delivery-mode", default="background", choices=["background", "foreground"])
    typ.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    # key
    key = sub.add_parser("key", help="Press key combination")
    key.add_argument("keys", help="Key combo, e.g. ctrl+s, return, escape")
    key.add_argument("--app", help="Target application name")
    key.add_argument("--delivery-mode", default="background", choices=["background", "foreground"])
    key.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    # scroll
    scr = sub.add_parser("scroll", help="Scroll")
    scr.add_argument("direction", choices=["up", "down", "left", "right"])
    scr.add_argument("--amount", type=int, default=3, help="Scroll ticks (default 3)")
    scr.add_argument("--app", help="Target application name")
    scr.add_argument("--delivery-mode", default="background", choices=["background", "foreground"])

    # drag
    drg = sub.add_parser("drag", help="Drag from one point to another")
    drg.add_argument("--from-element", type=int, help="Source SOM element index")
    drg.add_argument("--from-coordinate", nargs=2, type=int, metavar=("X", "Y"), help="Source [x, y]")
    drg.add_argument("--to-element", type=int, help="Target SOM element index")
    drg.add_argument("--to-coordinate", nargs=2, type=int, metavar=("X", "Y"), help="Target [x, y]")
    drg.add_argument("--app", help="Target application name")
    drg.add_argument("--delivery-mode", default="background", choices=["background", "foreground"])
    drg.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    # list_apps
    sub.add_parser("list-apps", help="List running applications")

    # list_windows
    sub.add_parser("list-windows", help="List open windows")

    # focus_app
    foc = sub.add_parser("focus-app", help="Focus an application")
    foc.add_argument("app", help="Application name")
    foc.add_argument("--raise-window", action="store_true", help="Bring window to front")

    args = parser.parse_args(argv)

    if not args.desktop_action:
        parser.print_help()
        return 1

    app_name = getattr(args, "app", None)

    if args.desktop_action == "capture":
        result = capture(app=args.app, mode=args.mode)
        print(result.get("message", result.get("error", "Unknown result")))
        if result.get("screenshot_path"):
            print(f"Screenshot saved: {result['screenshot_path']}")
        return 0 if result["ok"] else 1

    if args.desktop_action == "click":
        target = f"element #{args.element}" if args.element else f"coordinate {args.coordinate}"
        if not args.confirm and _desktop_confirm("click", target):
            print("Cancelled by user.")
            return 0
        result = click(
            element=args.element,
            coordinate=args.coordinate,
            app=args.app,
            button=args.button,
            delivery_mode=args.delivery_mode,
        )
        print(result.get("message", result.get("error", "Unknown result")))
        if result.get("screenshot_path"):
            print(f"Screenshot: {result['screenshot_path']}")
        return 0 if result["ok"] else 1

    if args.desktop_action == "type":
        if not args.confirm and _desktop_confirm("type", args.text):
            print("Cancelled by user.")
            return 0
        result = type_text(text=args.text, app=args.app, delivery_mode=args.delivery_mode)
        print(result.get("message", result.get("error", "Unknown result")))
        return 0 if result["ok"] else 1

    if args.desktop_action == "key":
        if not args.confirm and _desktop_confirm("key", args.keys):
            print("Cancelled by user.")
            return 0
        result = press_keys(keys=args.keys, app=args.app, delivery_mode=args.delivery_mode)
        print(result.get("message", result.get("error", "Unknown result")))
        return 0 if result["ok"] else 1

    if args.desktop_action == "scroll":
        result = scroll(
            direction=args.direction,
            amount=args.amount,
            app=args.app,
            delivery_mode=args.delivery_mode,
        )
        print(result.get("message", result.get("error", "Unknown result")))
        return 0 if result["ok"] else 1

    if args.desktop_action == "drag":
        if not args.confirm and _desktop_confirm("drag", f"{args.app or 'frontmost'}"):
            print("Cancelled by user.")
            return 0
        result = drag(
            from_element=args.from_element,
            from_coordinate=args.from_coordinate,
            to_element=args.to_element,
            to_coordinate=args.to_coordinate,
            app=args.app,
            delivery_mode=args.delivery_mode,
        )
        print(result.get("message", result.get("error", "Unknown result")))
        return 0 if result["ok"] else 1

    if args.desktop_action == "list-apps":
        result = list_apps()
        print(result.get("message", result.get("error", "Unknown result")))
        for a in result.get("apps", []):
            print(f"  - {a}")
        return 0 if result["ok"] else 1

    if args.desktop_action == "list-windows":
        result = list_windows()
        print(result.get("message", result.get("error", "Unknown result")))
        for w in result.get("windows", []):
            print(f"  - {w}")
        return 0 if result["ok"] else 1

    if args.desktop_action == "focus-app":
        result = focus_app(app=args.app, raise_window=args.raise_window)
        print(result.get("message", result.get("error", "Unknown result")))
        return 0 if result["ok"] else 1

    parser.print_help()
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deskbridge")
    parser.add_argument("app", help="Application wrapper name, 'install', 'log', 'chart', or 'desktop'")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command and arguments for the wrapper or desktop subcommand",
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
        output_path = generate_chart()
        print(f"[OK] Chart generated: {output_path}")
        return

    if args.app == "desktop":
        sys.exit(_handle_desktop(args.command))

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