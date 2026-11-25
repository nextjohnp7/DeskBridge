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

## Completed
- [x] Blender render wrapper
- [x] Core loader + confirmation
- [x] Simple CLI-Hub registry
- [x] Second application wrapper (GIMP)
- [x] Install command (`deskbridge install <app>`)
- [x] Production CLI-Hub (waitress)