"""Activity log tracking for DeskBridge.

Records every wrapper action and confirmation decision executed through
the CLI, including timestamp, wrapper name, action, input arguments,
and result status.

Security properties:

- **Sensitive data sanitization:** Args and messages are scanned for
  potentially sensitive values (file paths, text content, credentials)
  and redacted before being written to the log file.
- **Log rotation:** When the log file exceeds ``MAX_LOG_SIZE_BYTES``,
  it is rotated to ``activity.log.1``, ``activity.log.2``, etc., up to
  ``MAX_LOG_ROTATIONS``. Oldest rotations are deleted.
- **Retention:** Log records older than ``RETENTION_DAYS`` are
  automatically removed on each write. Set to 0 to disable.
- **Local-only:** Logs are never transmitted to a remote server.

Log format: one JSON object per line (JSON Lines / NDJSON).

Example record:

    {
      "timestamp": "2026-11-26T10:30:00.123456",
      "version": 1,
      "app": "blender",
      "action": "render",
      "args": {"file": "[REDACTED]", "output": "[REDACTED]"},
      "status": "success",
      "message": "Render completed"
    }

Status values: "success", "failed", "rejected", "cancelled".
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "activity.log")

# --- Configuration ---
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB per log file
MAX_LOG_ROTATIONS = 5                   # Keep up to 5 rotated files
RETENTION_DAYS = 30                     # Auto-delete records older than 30 days (0 = disabled)

# Patterns that indicate potentially sensitive values in args/messages.
# Values matching these patterns are replaced with "[REDACTED]".
SENSITIVE_PATTERNS = [
    re.compile(r"^(.*?)(?:password|passwd|pwd|secret|token|api[_-]?key|credential)(.*?)$", re.IGNORECASE),
    re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),  # base64-like blobs
    re.compile(r"^[a-fA-F0-9]{32,}$"),            # hex hashes / IDs
]

# Keys that are always redacted regardless of value.
ALWAYS_REDACT_KEYS = {
    "password", "passwd", "pwd", "secret", "token",
    "api_key", "apikey", "access_token", "refresh_token",
    "client_secret", "credential", "auth",
}

# Keys whose values are file paths or text content that may be sensitive.
# The value is replaced with "[REDACTED]" but the key is kept for audit.
REDACT_VALUE_KEYS = {
    "file", "path", "text", "content", "output", "input",
    "source", "destination", "keys", "message",
}


def ensure_log_dir() -> None:
    """Create the logs directory if it does not exist."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def _is_sensitive_key(key: str) -> bool:
    """Return True if the key name indicates a sensitive value."""
    return key.lower() in ALWAYS_REDACT_KEYS or key.lower() in REDACT_VALUE_KEYS


def _is_sensitive_value(value: Any) -> bool:
    """Return True if the value looks sensitive (credential, token, hash, etc.)."""
    if not isinstance(value, str):
        return False
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            return True
    return False


def sanitize_for_log(args: Any) -> Any:
    """Return a copy of args with sensitive values redacted.

    Keys that are always sensitive (e.g. password, token) have their
    values replaced with "[REDACTED]". File paths and text content are
    also redacted but the key is preserved for audit purposes.

    Args that are not dicts are returned unchanged.
    """
    if isinstance(args, dict):
        sanitized: dict[str, Any] = {}
        for key, value in args.items():
            if _is_sensitive_key(key) or _is_sensitive_value(value):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_log(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    sanitize_for_log(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    return args


def _rotate_if_needed() -> None:
    """Rotate the log file if it exceeds MAX_LOG_SIZE_BYTES."""
    if not os.path.exists(LOG_FILE):
        return
    try:
        size = os.path.getsize(LOG_FILE)
    except OSError:
        return
    if size < MAX_LOG_SIZE_BYTES:
        return

    # Shift existing rotations: .4 -> .5 (delete), .3 -> .4, etc.
    for i in range(MAX_LOG_ROTATIONS - 1, 0, -1):
        src = f"{LOG_FILE}.{i}"
        dst = f"{LOG_FILE}.{i + 1}"
        if os.path.exists(dst):
            os.remove(dst)
        if os.path.exists(src):
            os.rename(src, dst)

    # Move current log to .1
    if os.path.exists(f"{LOG_FILE}.1"):
        os.remove(f"{LOG_FILE}.1")
    os.rename(LOG_FILE, f"{LOG_FILE}.1")


def _apply_retention() -> None:
    """Remove log records older than RETENTION_DAYS from all log files."""
    if RETENTION_DAYS <= 0:
        return

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    files_to_clean = [LOG_FILE]
    for i in range(1, MAX_LOG_ROTATIONS + 1):
        rotated = f"{LOG_FILE}.{i}"
        if os.path.exists(rotated):
            files_to_clean.append(rotated)

    for path in files_to_clean:
        if not os.path.exists(path):
            continue
        kept_lines: list[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ts_str = record.get("timestamp", "")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                kept_lines.append(line)
                        else:
                            kept_lines.append(line)
                    except (json.JSONDecodeError, ValueError):
                        # Keep unparseable lines to avoid data loss
                        kept_lines.append(line)
        except OSError:
            continue

        with open(path, "w", encoding="utf-8") as f:
            for line in kept_lines:
                f.write(line + "\n")


def record_action(
    app_name: str,
    action: str,
    args: dict,
    status: str,
    message: str = "",
) -> None:
    """Append an action record to the activity log.

    Parameters
    ----------
    app_name : str
        Name of the wrapper (e.g., "blender").
    action : str
        Action performed (e.g., "render_scene").
    args : dict
        Input arguments passed to the action. Sensitive values are
        redacted before writing.
    status : str
        One of: "success", "failed", "rejected", "cancelled".
    message : str
        Optional detail message (e.g., output path or error text).
        Sensitive content is redacted.

    Raises
    ------
    ValueError
        If status is not one of the allowed values.
    """
    allowed_statuses = {"success", "failed", "rejected", "cancelled"}
    if status not in allowed_statuses:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of {sorted(allowed_statuses)}"
        )

    ensure_log_dir()
    _rotate_if_needed()

    record = {
        "timestamp": datetime.now().isoformat(),
        "version": 1,
        "app": app_name,
        "action": action,
        "args": sanitize_for_log(args),
        "status": status,
        "message": sanitize_for_log(message) if isinstance(message, str) else message,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _apply_retention()


def read_logs(limit: int | None = None) -> list[dict]:
    """Read activity log records, newest first.

    Parameters
    ----------
    limit : int | None
        Maximum number of records to return. None returns all records.

    Returns
    -------
    list[dict]
        List of log records. Corrupt lines are skipped with a warning
        printed to stderr.
    """
    ensure_log_dir()
    if not os.path.exists(LOG_FILE):
        return []

    records: list[dict] = []
    files_to_read = [LOG_FILE]
    for i in range(1, MAX_LOG_ROTATIONS + 1):
        rotated = f"{LOG_FILE}.{i}"
        if os.path.exists(rotated):
            files_to_read.append(rotated)

    for path in files_to_read:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(
                            f"[WARNING] Skipping corrupt log line in {path}",
                            file=sys.stderr,
                        )
        except OSError:
            continue

    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    if limit is not None:
        records = records[:limit]
    return records


def clear_logs() -> None:
    """Remove all activity log records, including rotated files."""
    ensure_log_dir()
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    for i in range(1, MAX_LOG_ROTATIONS + 1):
        rotated = f"{LOG_FILE}.{i}"
        if os.path.exists(rotated):
            os.remove(rotated)


def get_log_stats() -> dict:
    """Return summary statistics about the activity log.

    Returns
    -------
    dict
        Keys: total_entries, status_counts, app_counts, action_counts,
        oldest_timestamp, newest_timestamp, log_file_exists,
        log_file_size_bytes.
    """
    records = read_logs()
    status_counts: dict[str, int] = {}
    app_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    timestamps: list[str] = []

    for r in records:
        status = r.get("status", "unknown")
        app = r.get("app", "unknown")
        action = r.get("action", "unknown")
        ts = r.get("timestamp", "")

        status_counts[status] = status_counts.get(status, 0) + 1
        app_counts[app] = app_counts.get(app, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1
        if ts:
            timestamps.append(ts)

    log_exists = os.path.exists(LOG_FILE)
    log_size = 0
    if log_exists:
        try:
            log_size = os.path.getsize(LOG_FILE)
        except OSError:
            log_size = 0

    return {
        "total_entries": len(records),
        "status_counts": status_counts,
        "app_counts": app_counts,
        "action_counts": action_counts,
        "oldest_timestamp": min(timestamps) if timestamps else None,
        "newest_timestamp": max(timestamps) if timestamps else None,
        "log_file_exists": log_exists,
        "log_file_size_bytes": log_size,
    }