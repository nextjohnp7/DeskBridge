"""End-to-end verification for DeskBridge wrapper discovery and CLI behavior."""

import importlib.util
import json
import os
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
    """Wrapper CLI help runs without error."""
    import importlib.util

    for app in ["blender", "gimp"]:
        cli_path = os.path.join(WRAPPERS_DIR, app, "cli.py")
        spec = importlib.util.spec_from_file_location(f"{app}_cli", cli_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # argparse --help should print and exit 0
        try:
            module.main(["--help"])
        except SystemExit as exc:
            assert exc.code == 0, f"{app} --help exited with {exc.code}"
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


def test_desktop_control_requires_hermes_agent():
    """Desktop control functions return clear error outside Hermes agent context."""
    from core.desktop_control import capture, click, type_text, press_keys, scroll, drag, list_apps, list_windows, focus_app

    # All functions should return ok=False with a clear error message
    result = capture()
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = click(element=1)
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = type_text("hello")
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = press_keys("return")
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = scroll("down")
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = drag(from_element=1, to_element=2)
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = list_apps()
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = list_windows()
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    result = focus_app("TestApp")
    assert result["ok"] is False
    assert "No desktop backend is available" in result.get("message", "")

    print("Desktop control correctly reports no backend available")


def test_mcp_server_builds():
    """MCP server can be built and lists tools."""
    from core.mcp_server import build_server

    server = build_server()
    assert server is not None
    assert server.name == "deskbridge"
    print("MCP server builds successfully")


def test_mcp_server_tools():
    """MCP server exposes expected tools."""
    from core.mcp_server import build_server
    import mcp.types as types
    import asyncio

    server = build_server()

    # Get the registered list_tools handler
    handler = server.request_handlers[types.ListToolsRequest]
    result = asyncio.run(handler(None))
    # MCP returns ServerResult(root=ListToolsResult(tools=[...]))
    tools = result.root.tools if hasattr(result, "root") else result
    tool_names = {t.name for t in tools}
    expected = {
        "desktop_capture",
        "desktop_click",
        "desktop_type",
        "desktop_key",
        "desktop_scroll",
        "desktop_drag",
        "desktop_list_apps",
        "desktop_list_windows",
        "desktop_focus_app",
        "desktop_list_backends",
        "wrapper_call",
        "wrapper_install",
        "wrapper_list",
        "activity_log_read",
        "activity_chart_generate",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"
    print(f"MCP server exposes {len(tools)} tools")


def test_mcp_dispatch_unknown_tool():
    """MCP dispatch returns error for unknown tool."""
    from core.mcp_server import _dispatch

    result = _dispatch("nonexistent_tool", {})
    assert result["ok"] is False
    assert "Unknown tool" in result.get("error", "")
    print("MCP dispatch handles unknown tool")


def test_confirm_low_risk_auto_approves():
    """Low-risk actions are auto-approved without prompt."""
    from core.confirm import confirm_action, LOW

    result = confirm_action(LOW, "capture screenshot", app="desktop", action="capture")
    assert result is True
    print("Low-risk action auto-approves")


def test_confirm_medium_rejects_non_interactive():
    """Medium/high-risk actions rejected in non-interactive mode without --confirm."""
    from core.confirm import confirm_action, MEDIUM, ConfirmationError
    from unittest.mock import patch

    with patch("sys.stdin.isatty", return_value=False):
        try:
            confirm_action(MEDIUM, "click element", app="desktop", action="click")
            assert False, "Expected ConfirmationError in non-interactive mode"
        except ConfirmationError:
            pass
    print("Medium-risk action rejected in non-interactive mode without --confirm")


def test_confirm_medium_approves_with_confirm_flag():
    """Medium/high-risk actions approved with --confirm flag in non-interactive mode."""
    from core.confirm import confirm_action, MEDIUM, HIGH

    assert confirm_action(MEDIUM, "click element", confirm=True, app="desktop", action="click") is True
    assert confirm_action(HIGH, "press keys", confirm=True, app="desktop", action="key") is True
    print("Medium/high-risk action approved with --confirm flag")


def test_validate_unknown_app_rejected():
    """Unknown application is rejected by allowlist."""
    from core.confirm import validate_action_permitted, ConfirmationError

    try:
        validate_action_permitted("nonexistent_app", "some_action")
        assert False, "Expected ConfirmationError for unknown app"
    except ConfirmationError as exc:
        assert "not installed or not allowed" in str(exc)
    print("Unknown application rejected by allowlist")


def test_validate_unknown_action_rejected():
    """Unknown action for a known app is rejected by allowlist."""
    from core.confirm import validate_action_permitted, ConfirmationError

    try:
        validate_action_permitted("blender", "nonexistent_action")
        assert False, "Expected ConfirmationError for unknown action"
    except ConfirmationError as exc:
        assert "not declared" in str(exc)
    print("Unknown action rejected by allowlist")


def test_validate_blocked_app_rejected():
    """Blocked application is rejected even if installed."""
    from core.confirm import validate_action_permitted, ConfirmationError, BLOCKED_APPS

    BLOCKED_APPS.add("dangerous_app")
    try:
        validate_action_permitted("dangerous_app", "some_action")
        assert False, "Expected ConfirmationError for blocked app"
    except ConfirmationError as exc:
        assert "block list" in str(exc)
    finally:
        BLOCKED_APPS.discard("dangerous_app")
    print("Blocked application rejected")


def test_validate_parameter_type_error():
    """Wrong parameter type is rejected."""
    from core.confirm import validate_parameter, ConfirmationError

    try:
        validate_parameter("count", "not_a_number", int)
        assert False, "Expected ConfirmationError for wrong type"
    except ConfirmationError as exc:
        assert "integer" in str(exc)
    print("Wrong parameter type rejected")


def test_validate_parameter_range_error():
    """Out-of-range parameter is rejected."""
    from core.confirm import validate_parameter, ConfirmationError

    try:
        validate_parameter("level", 999, int, min_value=1, max_value=100)
        assert False, "Expected ConfirmationError for out of range"
    except ConfirmationError as exc:
        assert "<= 100" in str(exc)
    print("Out-of-range parameter rejected")


def test_validate_coordinates_invalid():
    """Invalid coordinate pair is rejected."""
    from core.confirm import validate_coordinates, ConfirmationError

    try:
        validate_coordinates([1, 2, 3])
        assert False, "Expected ConfirmationError for invalid coordinates"
    except ConfirmationError:
        pass
    try:
        validate_coordinates([-1, 5])
        assert False, "Expected ConfirmationError for negative coordinate"
    except ConfirmationError:
        pass
    result = validate_coordinates([100, 200])
    assert result == [100, 200]
    print("Invalid coordinates rejected, valid coordinates accepted")


# --- Activity logging tests ---

def test_activity_log_sanitizes_sensitive_keys():
    """Sensitive keys (password, token, file path) are redacted in log."""
    from core.activity_log import record_action, read_logs, clear_logs

    clear_logs()
    record_action(
        "testapp",
        "testaction",
        {"password": "secret123", "file": "/path/to/secret.blend", "count": 5},
        "success",
        "done",
    )
    logs = read_logs()
    assert len(logs) == 1
    assert logs[0]["args"]["password"] == "[REDACTED]"
    assert logs[0]["args"]["file"] == "[REDACTED]"
    assert logs[0]["args"]["count"] == 5
    print("Activity log sanitizes sensitive keys")


def test_activity_log_sanitizes_sensitive_values():
    """Values that look like tokens/hashes are redacted."""
    from core.activity_log import record_action, read_logs, clear_logs

    clear_logs()
    record_action(
        "testapp",
        "testaction",
        {"token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"},
        "success",
        "done",
    )
    logs = read_logs()
    assert len(logs) == 1
    assert logs[0]["args"]["token"] == "[REDACTED]"
    print("Activity log sanitizes sensitive values")


def test_activity_log_rejects_invalid_status():
    """record_action raises ValueError for invalid status."""
    from core.activity_log import record_action

    try:
        record_action("testapp", "testaction", {}, "invalid_status")
        assert False, "Expected ValueError for invalid status"
    except ValueError:
        pass
    print("Activity log rejects invalid status")


def test_activity_log_get_stats():
    """get_log_stats returns correct summary."""
    from core.activity_log import record_action, read_logs, clear_logs, get_log_stats

    clear_logs()
    record_action("app1", "action1", {}, "success", "")
    record_action("app1", "action2", {}, "failed", "error")
    record_action("app2", "action1", {}, "success", "")

    stats = get_log_stats()
    assert stats["total_entries"] == 3
    assert stats["status_counts"]["success"] == 2
    assert stats["status_counts"]["failed"] == 1
    assert stats["app_counts"]["app1"] == 2
    assert stats["app_counts"]["app2"] == 1
    assert stats["log_file_exists"] is True
    print("Activity log stats correct")


def test_activity_log_clear_removes_all():
    """clear_logs removes all records."""
    from core.activity_log import record_action, read_logs, clear_logs

    clear_logs()
    record_action("app1", "action1", {}, "success", "")
    assert len(read_logs()) == 1
    clear_logs()
    assert len(read_logs()) == 0
    print("Activity log clear removes all records")


def test_activity_log_read_limit():
    """read_logs respects limit parameter."""
    from core.activity_log import record_action, read_logs, clear_logs

    clear_logs()
    for i in range(5):
        record_action("app1", f"action{i}", {}, "success", "")
    logs = read_logs(limit=3)
    assert len(logs) == 3
    print("Activity log read limit works")


if __name__ == "__main__":
    test_wrapper_discovery_finds_all_wrappers()
    test_manifest_has_required_fields()
    test_cli_help_runs()
    test_activity_log_record_and_read()
    test_chart_generator_creates_file()
    test_desktop_control_requires_hermes_agent()
    test_mcp_server_builds()
    test_mcp_server_tools()
    test_mcp_dispatch_unknown_tool()
    test_confirm_low_risk_auto_approves()
    test_confirm_medium_rejects_non_interactive()
    test_confirm_medium_approves_with_confirm_flag()
    test_validate_unknown_app_rejected()
    test_validate_unknown_action_rejected()
    test_validate_blocked_app_rejected()
    test_validate_parameter_type_error()
    test_validate_parameter_range_error()
    test_validate_coordinates_invalid()
    test_activity_log_sanitizes_sensitive_keys()
    test_activity_log_sanitizes_sensitive_values()
    test_activity_log_rejects_invalid_status()
    test_activity_log_get_stats()
    test_activity_log_clear_removes_all()
    test_activity_log_read_limit()
    print("\nAll checks passed.")
