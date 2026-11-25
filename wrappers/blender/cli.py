"""CLI entry point for the Blender wrapper."""

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
from .actions import render_scene


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deskbridge blender")
    sub = parser.add_subparsers(dest="command")

    render_p = sub.add_parser("render", help="Render a Blender scene")
    render_p.add_argument("--file", required=True, help="Path to .blend file")
    render_p.add_argument("--output", required=True, help="Path to output file")
    render_p.add_argument(
        "--confirm",
        action="store_true",
        help="Accept confirmation without interactive prompt (for automation)",
    )

    args = parser.parse_args(argv)

    if args.command == "render":
        description = f"Render {args.file} to {args.output}"
        if args.confirm or confirm_action("medium", description):
            result = render_scene(args.file, args.output)
            if result["ok"]:
                print(f"[OK] {result['message']}")
            else:
                print(f"[FAILED] {result['error']}")
                sys.exit(1)
        else:
            print("Cancelled by user.")
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)