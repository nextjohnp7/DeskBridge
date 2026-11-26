"""MCP server for DeskBridge.

Exposes DeskBridge capabilities (desktop control, wrapper execution,
activity log, chart generation) as MCP tools so AI agents like Claude
Desktop, Cursor, and other MCP-compatible agents can connect directly.

Run over stdio:

    python core/mcp_server.py

Or configure in ~/.hermes/config.yaml:

    mcp_servers:
      deskbridge:
        command: "python"
        args: ["path/to/DeskBridge/core/mcp_server.py"]
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

try:
    from mcp.server import Server
    import mcp.server.stdio
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from core.activity_log import read_logs
from core.chart_generator import generate_chart
from core.desktop_control import (
    capture, click, type_text, press_keys, scroll, drag,
    list_apps, list_windows, focus_app,
    list_backends, active_backend,
)
from core.installer import install_wrapper
from core.loader import load_wrapper

SERVER_NAME = "deskbridge"


def build_server() -> Server:
    """Build and configure the MCP server with all DeskBridge tools."""
    server = Server(SERVER_NAME)

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List all available DeskBridge MCP tools."""
        return [
            types.Tool(
                name="desktop_capture",
                description="Capture a screenshot of the desktop or a specific app",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app": {"type": "string", "description": "Target application name (optional)"},
                        "mode": {"type": "string", "enum": ["som", "vision", "ax"], "default": "som", "description": "Capture mode"},
                    },
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_click",
                description="Click an element by SOM index or raw coordinate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "element": {"type": "integer", "description": "SOM element index (1-based)"},
                        "coordinate": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2, "description": "[x, y] pixel coordinates"},
                        "app": {"type": "string", "description": "Target application name"},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                        "confirm": {"type": "boolean", "default": False, "description": "Skip confirmation prompt"},
                    },
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_type",
                description="Type text into the focused field of the target app",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to type"},
                        "app": {"type": "string", "description": "Target application name"},
                        "confirm": {"type": "boolean", "default": False, "description": "Skip confirmation prompt"},
                    },
                    "required": ["text"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_key",
                description="Press a key combination (e.g. ctrl+s, return, escape)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keys": {"type": "string", "description": "Key combination"},
                        "app": {"type": "string", "description": "Target application name"},
                        "confirm": {"type": "boolean", "default": False, "description": "Skip confirmation prompt"},
                    },
                    "required": ["keys"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_scroll",
                description="Scroll in the target app",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Scroll direction"},
                        "amount": {"type": "integer", "default": 3, "description": "Scroll wheel ticks"},
                        "app": {"type": "string", "description": "Target application name"},
                    },
                    "required": ["direction"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_drag",
                description="Drag from one element/coordinate to another",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_element": {"type": "integer", "description": "Source SOM element index"},
                        "from_coordinate": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2, "description": "Source [x, y]"},
                        "to_element": {"type": "integer", "description": "Target SOM element index"},
                        "to_coordinate": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2, "description": "Target [x, y]"},
                        "app": {"type": "string", "description": "Target application name"},
                        "confirm": {"type": "boolean", "default": False, "description": "Skip confirmation prompt"},
                    },
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_list_apps",
                description="List running applications",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_list_windows",
                description="List open windows",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_focus_app",
                description="Focus (bring input focus to) an application",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app": {"type": "string", "description": "Application name"},
                        "raise_window": {"type": "boolean", "default": False, "description": "Bring window to front"},
                    },
                    "required": ["app"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="desktop_list_backends",
                description="List available desktop control backends",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="wrapper_call",
                description="Call an action on a DeskBridge wrapper",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app": {"type": "string", "description": "Wrapper name (e.g. blender, gimp)"},
                        "action": {"type": "string", "description": "Action name (e.g. render, export)"},
                        "args": {"type": "object", "description": "Action arguments as key-value pairs"},
                        "confirm": {"type": "boolean", "default": False, "description": "Skip confirmation prompt"},
                    },
                    "required": ["app", "action"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="wrapper_install",
                description="Install a new wrapper scaffold",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Name of the wrapper to install"},
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="wrapper_list",
                description="List all installed wrappers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="activity_log_read",
                description="Read recent activity log entries",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 10, "description": "Maximum number of entries to return"},
                    },
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="activity_chart_generate",
                description="Generate an SVG bar chart of activity statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "description": "Path to save the SVG file"},
                    },
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        """Handle a tool call from an MCP client."""
        try:
            result = _dispatch(name, arguments or {})
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        text = json.dumps(result, indent=2, ensure_ascii=False)
        return [types.TextContent(type="text", text=text)]

    return server


def _dispatch(name: str, arguments: dict[str, Any]) -> dict:
    """Dispatch a tool call to the appropriate DeskBridge function."""
    # --- Desktop control ---
    if name == "desktop_capture":
        return capture(app=arguments.get("app"), mode=arguments.get("mode", "som"))

    if name == "desktop_click":
        return click(
            element=arguments.get("element"),
            coordinate=arguments.get("coordinate"),
            app=arguments.get("app"),
            button=arguments.get("button", "left"),
        )

    if name == "desktop_type":
        return type_text(
            text=arguments["text"],
            app=arguments.get("app"),
        )

    if name == "desktop_key":
        return press_keys(
            keys=arguments["keys"],
            app=arguments.get("app"),
        )

    if name == "desktop_scroll":
        return scroll(
            direction=arguments["direction"],
            amount=arguments.get("amount", 3),
            app=arguments.get("app"),
        )

    if name == "desktop_drag":
        return drag(
            from_element=arguments.get("from_element"),
            from_coordinate=arguments.get("from_coordinate"),
            to_element=arguments.get("to_element"),
            to_coordinate=arguments.get("to_coordinate"),
            app=arguments.get("app"),
        )

    if name == "desktop_list_apps":
        return list_apps()

    if name == "desktop_list_windows":
        return list_windows()

    if name == "desktop_focus_app":
        return focus_app(
            app=arguments["app"],
            raise_window=arguments.get("raise_window", False),
        )

    if name == "desktop_list_backends":
        return {
            "ok": True,
            "backends": list_backends(),
            "active": active_backend(),
        }

    # --- Wrapper management ---
    if name == "wrapper_call":
        app = arguments["app"]
        action = arguments["action"]
        args = arguments.get("args", {})
        try:
            manifest, cli_module = load_wrapper(app)
        except Exception as exc:
            return {"ok": False, "error": f"Unable to load wrapper '{app}': {exc}"}

        # Build CLI args from the args dict
        cli_args = [action]
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    cli_args.append(f"--{key}")
            else:
                cli_args.append(f"--{key}")
                cli_args.append(str(value))

        try:
            cli_module.main(cli_args)
            return {"ok": True, "message": f"Wrapper '{app}' action '{action}' completed"}
        except SystemExit as exc:
            if exc.code == 0:
                return {"ok": True, "message": f"Wrapper '{app}' action '{action}' completed"}
            return {"ok": False, "error": f"Wrapper '{app}' action '{action}' failed with exit code {exc.code}"}

    if name == "wrapper_install":
        return install_wrapper(arguments["app_name"])

    if name == "wrapper_list":
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        wrappers_dir = os.path.join(base_dir, "wrappers")
        wrappers = []
        if os.path.isdir(wrappers_dir):
            for name in sorted(os.listdir(wrappers_dir)):
                manifest_path = os.path.join(wrappers_dir, name, "manifest.json")
                if os.path.isfile(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                        wrappers.append(manifest)
                    except (json.JSONDecodeError, OSError):
                        continue
        return {"ok": True, "wrappers": wrappers, "count": len(wrappers)}

    # --- Activity log ---
    if name == "activity_log_read":
        limit = arguments.get("limit")
        logs = read_logs(limit)
        return {"ok": True, "logs": logs, "count": len(logs)}

    if name == "activity_chart_generate":
        output_path = arguments.get("output_path")
        path = generate_chart(output_path)
        return {"ok": True, "message": f"Chart generated: {path}", "path": path}

    return {"ok": False, "error": f"Unknown tool: {name}"}


def main() -> None:
    """Entry point for running the MCP server over stdio."""
    if not MCP_AVAILABLE:
        print(
            "Error: mcp package not installed. Run: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    server = build_server()
    initialization_options = server.create_initialization_options()

    async def _run() -> None:
        async with mcp.server.stdio.stdio_server() as (
            read_stream,
            write_stream,
        ):
            await server.run(
                read_stream,
                write_stream,
                initialization_options,
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
