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
    args: ["path/to/DeskBridge/mcp_server.py"]
```

Replace `path/to/DeskBridge/mcp_server.py` with the actual path to your DeskBridge installation. Restart Hermes Agent. The MCP tools become available as `mcp_deskbridge_*` in every conversation.

### Configure in Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "deskbridge": {
      "command": "python",
      "args": ["path/to/DeskBridge/mcp_server.py"]
    }
  }
}
```

Replace `path/to/DeskBridge/mcp_server.py` with the actual path to your DeskBridge installation.

## Security Model

DeskBridge is designed to be safe, auditable, and transparent. Every action
passes through centralized security checks before execution.

### Safety confirmations

| Risk level | Behavior |
|------------|----------|
| **low** | Auto-approved, no prompt |
| **medium** | Requires explicit y/n confirmation (or `--confirm` flag) |
| **high** | Requires explicit y/n confirmation (or `--confirm` flag) |

**How confirmation works:**
1. User runs a medium/high-risk action (e.g. `click`, `type`, `key`, `drag`).
2. DeskBridge prints the action description and asks `Proceed? (y/n):`.
3. Only `y` approves; anything else cancels.
4. The `--confirm` flag skips the prompt (for automation/CI).
5. In non-interactive sessions (no TTY, e.g. CI/CD, MCP server), medium/high-risk actions are **rejected** unless `--confirm` is passed.
6. Every decision (approved/rejected/cancelled) is recorded to `logs/activity.log`.

### Allowlist (command restriction)

Only apps with an installed wrapper under `wrappers/<app>/manifest.json` can be executed.
Only actions declared in that manifest's `actions` field are permitted.
Unknown apps and unknown actions are **rejected before execution** with a clear error.

### Parameter validation

All parameters are validated for type and range before being passed to a wrapper:
- Integer parameters must be integers (string coercion attempted).
- Numeric parameters can have `min`/`max` bounds.
- Coordinate parameters must be `[x, y]` pairs within valid bounds.
- Invalid parameters raise a clear error and block execution.

### Blocked applications

Applications on the security block list (`BLOCKED_APPS` in `core.confirm`) are
rejected even if a wrapper is installed. Add dangerous system processes here.

### Activity logging

Every action and confirmation decision is recorded to `logs/activity.log` as
one JSON record per line (JSON Lines / NDJSON):

```json
{"timestamp": "2026-11-26T10:30:00.123456", "version": 1, "app": "blender", "action": "render", "args": {"file": "[REDACTED]", "output": "[REDACTED]"}, "status": "success", "message": "Render completed"}
```

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp when the action occurred |
| `version` | Log record schema version (currently `1`) |
| `app` | Wrapper/application name |
| `action` | Action performed |
| `args` | Input arguments (sensitive values redacted) |
| `status` | `success`, `failed`, `rejected`, or `cancelled` |
| `message` | Detail message (sensitive content redacted) |

**Sensitive data sanitization:** File paths, text content, passwords, tokens,
and other potentially sensitive values are automatically replaced with
`"[REDACTED]"` before being written. The key is preserved for audit purposes.

**Log rotation:** When `logs/activity.log` exceeds 10 MB, it is rotated to
`activity.log.1`, `activity.log.2`, etc., up to 5 rotations. Oldest rotations
are deleted automatically.

**Retention:** Log records older than 30 days are automatically removed on each
write. Set `RETENTION_DAYS = 0` in `core.activity_log.py` to disable.

**No API keys, tokens, passwords, or credentials are stored in code or logs.**

Read logs:
```bash
python deskbridge.py log [limit]
```

Get log statistics:
```python
from core.activity_log import get_log_stats
stats = get_log_stats()
# Returns total_entries, status_counts, app_counts, action_counts,
# oldest_timestamp, newest_timestamp, log_file_exists, log_file_size_bytes
```

Clear all logs (including rotated files):
```bash
# Programmatically:
from core.activity_log import clear_logs
clear_logs()
```


### Local validation before execution

All security checks (allowlist, parameter validation, confirmation) happen
**locally before** any desktop action or wrapper code is executed. Nothing is
sent to a remote server.
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