"""CLI entry point for the obsidian wrapper."""

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
    parser = argparse.ArgumentParser(prog="deskbridge obsidian")
    sub = parser.add_subparsers(dest="command")

    action_p = sub.add_parser("placeholder", help="Placeholder action for obsidian")
    action_p.add_argument("--input", required=True, help="Path to input file")
    action_p.add_argument("--output", required=True, help="Path to output file")
    action_p.add_argument(
        "--confirm",
        action="store_true",
        help="Accept confirmation without interactive prompt (for automation)",
    )

    args = parser.parse_args(argv)

    if args.command == "placeholder":
        description = f"Placeholder {args.input} to {args.output}"
        if args.confirm or confirm_action("medium", description):
            result = placeholder_action(args.input, args.output)
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
