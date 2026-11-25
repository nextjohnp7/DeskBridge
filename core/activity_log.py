"""Activity log tracking for DeskBridge.

Records every wrapper action executed through the CLI, including
timestamp, wrapper name, action, input arguments, and result status.
"""

import json
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "activity.log")


def ensure_log_dir():
    """Create the logs directory if it does not exist."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def record_action(app_name: str, action: str, args: dict, status: str, message: str = "") -> None:
    """Append an action record to the activity log.

    Parameters
    ----------
    app_name : str
        Name of the wrapper (e.g., "blender").
    action : str
        Action performed (e.g., "render_scene").
    args : dict
        Input arguments passed to the action.
    status : str
        "success" or "failed".
    message : str
        Optional detail message (e.g., output path or error text).
    """
    ensure_log_dir()
    record = {
        "timestamp": datetime.now().isoformat(),
        "app": app_name,
        "action": action,
        "args": args,
        "status": status,
        "message": message,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def read_logs(limit: int | None = None) -> list[dict]:
    """Read activity log records, newest first.

    Parameters
    ----------
    limit : int | None
        Maximum number of records to return. None returns all records.

    Returns
    -------
    list[dict]
        List of log records.
    """
    ensure_log_dir()
    if not os.path.exists(LOG_FILE):
        return []
    records = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records.reverse()
    if limit is not None:
        records = records[:limit]
    return records


def clear_logs() -> None:
    """Remove all activity log records."""
    ensure_log_dir()
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)