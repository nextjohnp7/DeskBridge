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

**Note:** Desktop control requires the Hermes agent environment (the `computer_use` tool is only available through the Hermes agent). Running `deskbridge.py desktop ...` outside the Hermes agent will return an error explaining this requirement.

## Completed
- [x] Blender render wrapper
- [x] Core loader + confirmation
- [x] Activity log tracking
- [x] Chart generation (SVG)
- [x] Desktop control (computer_use integration)
- [x] Simple CLI-Hub registry
- [x] Second application wrapper (GIMP)
- [x] Install command (`deskbridge install <app>`)
- [x] Web install via CLI-Hub (`POST /install/<app>`)
- [x] Production CLI-Hub (waitress)