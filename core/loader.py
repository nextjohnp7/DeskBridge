"""Load deskbridge wrappers from the wrappers/ directory."""

import importlib
import json
import os


def load_wrapper(app_name: str):
    """Load manifest and CLI module for a given app wrapper.

    Returns (manifest, cli_module).
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wrapper_dir = os.path.join(base_dir, "wrappers", app_name)
    manifest_path = os.path.join(wrapper_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Wrapper manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    cli_module = importlib.import_module(f"wrappers.{app_name}.cli")
    return manifest, cli_module