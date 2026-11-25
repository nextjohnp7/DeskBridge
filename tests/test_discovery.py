"""End-to-end verification for DeskBridge wrapper discovery and CLI behavior."""

import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
WRAPPERS_DIR = os.path.join(BASE_DIR, "wrappers")


def test_wrapper_discovery_finds_all_wrappers():
    found = []
    for name in sorted(os.listdir(WRAPPERS_DIR)):
        manifest_path = os.path.join(WRAPPERS_DIR, name, "manifest.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            found.append(manifest)

    names = {m["name"] for m in found}
    assert "blender" in names, "Blender wrapper not discovered"
    assert "gimp" in names, "GIMP wrapper not discovered"
    print(f"Discovered wrappers: {sorted(names)}")


def test_manifest_has_required_fields():
    for name in sorted(os.listdir(WRAPPERS_DIR)):
        manifest_path = os.path.join(WRAPPERS_DIR, name, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        assert "name" in m, f"{name}: missing 'name'"
        assert "version" in m, f"{name}: missing 'version'"
        assert "target_app" in m, f"{name}: missing 'target_app'"
        assert "description" in m, f"{name}: missing 'description'"
        assert "actions" in m, f"{name}: missing 'actions'"
        for action_name, action in m["actions"].items():
            assert "description" in action, f"{name}.{action_name}: missing 'description'"
            assert "risk" in action, f"{name}.{action_name}: missing 'risk'"
            assert "args" in action, f"{name}.{action_name}: missing 'args'"
    print("All manifests have required fields")


def test_cli_help_runs():
    for app in ["blender", "gimp"]:
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "deskbridge.py"), app, "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{app} --help failed: {result.stderr}"
        assert app in result.stdout.lower(), f"{app} --help output missing app name"
    print("CLI help runs for all wrappers")


def test_activity_log_record_and_read():
    """Activity log can record and read back entries."""
    from core.activity_log import record_action, read_logs, clear_logs, LOG_FILE

    clear_logs()
    record_action("testapp", "testaction", {"arg1": "val1"}, "success", "done")
    record_action("testapp", "testaction2", {"arg2": "val2"}, "failed", "error occurred")

    logs = read_logs()
    assert len(logs) == 2, f"Expected 2 log entries, got {len(logs)}"
    assert logs[0]["app"] == "testapp"
    assert logs[0]["action"] == "testaction2"
    assert logs[0]["status"] == "failed"
    assert logs[1]["app"] == "testapp"
    assert logs[1]["action"] == "testaction"
    assert logs[1]["status"] == "success"
    print("Activity log record and read works")


def test_chart_generator_creates_file():
    """Chart generator produces an SVG file."""
    from core.chart_generator import generate_chart

    output_path = generate_chart()
    assert os.path.exists(output_path), f"Chart file not created at {output_path}"
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content.startswith("<svg"), "Chart output is not valid SVG"
    print(f"Chart generator creates valid SVG: {output_path}")


if __name__ == "__main__":
    test_wrapper_discovery_finds_all_wrappers()
    test_manifest_has_required_fields()
    test_cli_help_runs()
    test_activity_log_record_and_read()
    test_chart_generator_creates_file()
    print("\nAll checks passed.")
