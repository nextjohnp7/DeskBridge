# DeskBridge

Universal interface for controlling desktop applications through AI agents.

## Structure
- `core/` — wrapper loader and confirmation layer
- `wrappers/` — per-application wrappers (starting with Blender)
- `tests/` — wrapper tests
- `deskbridge.py` — main CLI entry point

## Usage (MVP)
```bash
python deskbridge.py blender render --file scene.blend --output out.png --confirm
```

Without `--confirm`, a confirmation prompt is displayed for risky actions.

## Install a new wrapper
```bash
python deskbridge.py install <app_name>
```

Creates a scaffold under `wrappers/<app_name>/` with `manifest.json`, `actions.py`, and `cli.py`.

## Run CLI-Hub (registry website)
Development:
```bash
python hub/app.py
```
Then open `http://127.0.0.1:5000/`.

Production (waitress WSGI server):
```bash
python hub/run_production.py
```

## Activity log
```bash
python deskbridge.py log [limit]
```
Displays recent activity log entries (newest first). Optional `limit` restricts the number of entries.

## Chart generation
```bash
python deskbridge.py chart
```
Generates an SVG bar chart of activity statistics (success vs. failure per wrapper) and saves it to `reports/activity_chart.svg`.

## Desktop control
```bash
python deskbridge.py desktop <action> [options]
```

Controls any desktop application through screenshots, mouse clicks, keyboard input, scrolling, and dragging via the Hermes `computer_use` tool. Available actions:

- `capture` — Take a screenshot (`--app`, `--mode som|vision|ax`)
- `click` — Click an element (`--element`, `--coordinate X Y`, `--app`, `--button`, `--delivery-mode background|foreground`, `--confirm`)
- `type` — Type text (`text`, `--app`, `--delivery-mode`, `--confirm`)
- `key` — Press key combo (`keys`, e.g. `ctrl+s`, `return`, `--app`, `--delivery-mode`, `--confirm`)
- `scroll` — Scroll (`direction up|down|left|right`, `--amount`, `--app`, `--delivery-mode`)
- `drag` — Drag between elements (`--from-element`, `--from-coordinate X Y`, `--to-element`, `--to-coordinate X Y`, `--app`, `--delivery-mode`, `--confirm`)
- `list-apps` — List running applications
- `list-windows` — List open windows
- `focus-app` — Focus an application (`app`, `--raise-window`)

Risky actions (`click`, `type`, `key`, `drag`) require confirmation (`y/n`) unless `--confirm` is passed. All desktop actions are recorded in the activity log.

**Note:** Desktop control works with any registered backend. By default, DeskBridge tries the Hermes `computer_use` backend (when running inside the Hermes agent) and falls back to the PyAutoGUI backend (if `pip install pyautogui` has been done). If no backend is available, commands return a clear error explaining how to install one.

## Pluggable desktop backends

`core.desktop_control` uses a pluggable backend architecture so DeskBridge is
not locked to a single desktop automation vendor:

- `DesktopBackend` — abstract base class; subclass it to add a new backend.
- `HermesComputerUseBackend` — wraps the Hermes `computer_use` tool (cua-driver).
- `PyAutoGUIBackend` — wraps PyAutoGUI for cross-platform desktop control without the Hermes agent.
- `DesktopController` — auto-detects available backends and routes calls to the first one.

To add a non-Hermes backend (MCP, Claude Desktop, pyautogui, etc.):

```python
from core.desktop_control import DesktopBackend, register_backend

class MCPDesktopBackend(DesktopBackend):
    name = "mcp"
    def capture(self, app=None, mode="som"): ...
    def click(self, element=None, coordinate=None, app=None, ...): ...
    # implement all abstract methods

register_backend(MCPDesktopBackend())
```

Register backends before calling any desktop function. The controller tries
backends in registration order and uses the first available one.

## MCP Server (Model Context Protocol)

DeskBridge includes an MCP server so AI agents like Claude Desktop, Cursor,
and other MCP-compatible agents can connect directly without custom code.

### Run the MCP server

```bash
python mcp_server.py
```

The server communicates over stdio and exposes 15 tools:

| Tool | Description |
|------|-------------|
| `desktop_capture` | Capture screenshot |
| `desktop_click` | Click element/coordinate |
| `desktop_type` | Type text |
| `desktop_key` | Press key combination |
| `desktop_scroll` | Scroll |
| `desktop_drag` | Drag between points |
| `desktop_list_apps` | List running applications |
| `desktop_list_windows` | List open windows |
| `desktop_focus_app` | Focus an application |
| `desktop_list_backends` | List desktop backends |
| `wrapper_call` | Call a wrapper action |
| `wrapper_install` | Install a new wrapper |
| `wrapper_list` | List installed wrappers |
| `activity_log_read` | Read activity log |
| `activity_chart_generate` | Generate activity chart |

### Configure in Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  deskbridge:
    command: "python"
    args: ["D:/GitHub Project nextjohnp7/DeskBridge/mcp_server.py"]
```

Restart Hermes Agent. The MCP tools become available as `mcp_deskbridge_*`
in every conversation.

### Configure in Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "deskbridge": {
      "command": "python",
      "args": ["D:/GitHub Project nextjohnp7/DeskBridge/mcp_server.py"]
    }
  }
}
```

## Completed
- [x] Blender render wrapper
- [x] Core loader + confirmation
- [x] Activity log tracking
- [x] Chart generation (SVG)
- [x] Desktop control (computer_use + PyAutoGUI backends)
- [x] MCP server (15 tools for Claude Desktop, Cursor, etc.)
- [x] Simple CLI-Hub registry
- [x] Second application wrapper (GIMP)
- [x] Install command (`deskbridge install <app>`)
- [x] Web install via CLI-Hub (`POST /install/<app>`)
- [x] Production CLI-Hub (waitress)