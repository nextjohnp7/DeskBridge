"""CLI-Hub: simple registry website for DeskBridge wrappers.

Displays all wrappers available in the wrappers/ directory
and provides CLI commands for using them.
"""

import json
import os
import sys

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.installer import install_wrapper

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPERS_DIR = os.path.join(BASE_DIR, "wrappers")


def discover_wrappers():
    """Read all manifest.json files under wrappers/<app>/."""
    wrappers = []
    if not os.path.isdir(WRAPPERS_DIR):
        return wrappers

    for name in sorted(os.listdir(WRAPPERS_DIR)):
        manifest_path = os.path.join(WRAPPERS_DIR, name, "manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                manifest["_dir"] = name
                wrappers.append(manifest)
            except (json.JSONDecodeError, OSError):
                continue
    return wrappers


@app.route("/")
def index():
    wrappers = discover_wrappers()
    return render_template("index.html", wrappers=wrappers)


@app.route("/install/<app_name>", methods=["POST"])
def install(app_name: str):
    """Install a new wrapper scaffold via the web hub."""
    result = install_wrapper(app_name)
    if result["ok"]:
        return jsonify({"ok": True, "message": result["message"]})
    return jsonify({"ok": False, "error": result["error"]}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)