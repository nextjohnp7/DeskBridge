"""Confirmation layer for risky actions.

Provides a centralized, auditable confirmation mechanism:

- Low-risk actions: auto-approved without prompt.
- Medium/high-risk: require explicit y/n confirmation (unless --confirm flag).
- Non-interactive sessions (no TTY): medium/high rejected unless --confirm.
- All decisions (approve/reject/cancel) are recorded to the activity log.
- Allowlist check: only actions declared in a wrapper manifest are permitted.
- Unknown applications and unknown actions are rejected before execution.
- Parameter validation hooks for type and range checking.

This module is the single source of truth for safety decisions in DeskBridge.
No desktop action or wrapper call should execute without passing through
confirm_action() or validate_action_permitted() first.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


class ConfirmationError(Exception):
    """Raised when an action is rejected by the confirmation layer."""


LOW = "low"
MEDIUM = "medium"
HIGH = "high"

RISK_LEVELS = {LOW, MEDIUM, HIGH}

# Default risk levels for desktop control actions.
# Override per-app in manifest.json if needed.
DESKTOP_RISK_LEVELS = {
    "capture": LOW,
    "click": MEDIUM,
    "type": MEDIUM,
    "key": HIGH,
    "scroll": LOW,
    "drag": HIGH,
    "list_apps": LOW,
    "list_windows": LOW,
    "focus_app": MEDIUM,
}

# Applications explicitly blocked from execution (security deny-list).
# Add dangerous system processes here if needed.
BLOCKED_APPS: set[str] = set()


def is_interactive() -> bool:
    """Return True if stdin is attached to a TTY (interactive session)."""
    return sys.stdin.isatty()


def requires_confirmation(risk_level: str) -> bool:
    """Return True if the given risk level requires user confirmation."""
    return risk_level in (MEDIUM, HIGH)


def _project_root() -> str:
    """Return the DeskBridge project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_app_allowed(app_name: str) -> bool:
    """Check whether an application wrapper is installed and allowed.

    An app is allowed if it has a directory under wrappers/ with a
    manifest.json file and is not on the blocked list.
    """
    if app_name in BLOCKED_APPS:
        return False
    manifest_path = os.path.join(
        _project_root(), "wrappers", app_name, "manifest.json"
    )
    return os.path.isfile(manifest_path)


def is_action_allowed(app_name: str, action_name: str) -> bool:
    """Check whether an action is declared in the wrapper manifest.

    Returns False if the app is unknown or the action is not declared.
    """
    if not is_app_allowed(app_name):
        return False
    manifest_path = os.path.join(
        _project_root(), "wrappers", app_name, "manifest.json"
    )
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    actions = manifest.get("actions", {})
    return action_name in actions


def _log_decision(
    status: str,
    message: str,
    app: str | None = None,
    action: str | None = None,
    args: dict | None = None,
) -> None:
    """Record a confirmation decision to the activity log."""
    from core.activity_log import record_action

    record_action(
        app_name=app or "desktop",
        action=action or "unknown",
        args=args or {},
        status=status,
        message=message,
    )


def confirm_action(
    risk_level: str,
    description: str,
    confirm: bool = False,
    app: str | None = None,
    action: str | None = None,
    args: dict | None = None,
) -> bool:
    """Request user confirmation before executing a risky action.

    Args:
        risk_level: "low", "medium", or "high".
        description: Human-readable description of the action.
        confirm: If True, skip interactive prompt (automation mode).
        app: Target application name (for logging).
        action: Action name (for logging).
        args: Input arguments (for logging).

    Returns:
        True if the action is approved, False if cancelled by user.

    Raises:
        ConfirmationError: If risk_level is invalid, or if the action
            cannot proceed in non-interactive mode without --confirm.
    """
    if risk_level not in RISK_LEVELS:
        raise ConfirmationError(f"Invalid risk level: {risk_level!r}")

    # Low risk: always auto-approved
    if risk_level == LOW:
        _log_decision("success", "auto-approved (low risk)", app, action, args)
        return True

    # Automation mode: --confirm flag skips prompt
    if confirm:
        _log_decision("success", "auto-approved via --confirm", app, action, args)
        return True

    # Non-interactive and no --confirm: reject medium/high risk
    if not is_interactive():
        msg = (
            f"Cannot confirm [{risk_level}] action '{description}' "
            f"in non-interactive session without --confirm flag"
        )
        _log_decision("rejected", msg, app, action, args)
        raise ConfirmationError(msg)

    # Interactive: prompt user
    print(f"\n[DESKBRIDGE] Confirm action [{risk_level}]")
    print(f"Action: {description}")
    if app:
        print(f"Target app: {app}")
    answer = input("Proceed? (y/n): ").strip().lower()
    approved = answer == "y"

    status = "success" if approved else "cancelled"
    msg = "confirmed by user" if approved else "cancelled by user"
    _log_decision(status, msg, app, action, args)

    return approved


def validate_action_permitted(
    app_name: str, action_name: str, args: dict | None = None
) -> None:
    """Validate that an app and action are permitted before execution.

    Checks:
        1. App is not on the blocked list.
        2. App wrapper is installed (has manifest.json).
        3. Action is declared in the app manifest.

    Raises:
        ConfirmationError: If any check fails.
    """
    if app_name in BLOCKED_APPS:
        raise ConfirmationError(
            f"Application '{app_name}' is on the security block list "
            f"and cannot be executed."
        )

    if not is_app_allowed(app_name):
        raise ConfirmationError(
            f"Application '{app_name}' is not installed or not allowed. "
            f"Use 'deskbridge install {app_name}' to add it first."
        )

    if not is_action_allowed(app_name, action_name):
        raise ConfirmationError(
            f"Action '{action_name}' is not declared for application "
            f"'{app_name}'. Check wrappers/{app_name}/manifest.json "
            f"for available actions."
        )

    _log_decision(
        "success", "action permitted", app_name, action_name, args
    )


def validate_parameter(
    name: str,
    value: Any,
    expected_type: type,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    allowed_values: list | None = None,
) -> Any:
    """Validate a single parameter value.

    Args:
        name: Parameter name (for error messages).
        value: The value to validate.
        expected_type: Expected Python type (int, str, bool, etc.).
        min_value: Minimum allowed value (for int/float).
        max_value: Maximum allowed value (for int/float).
        allowed_values: List of allowed values (membership check).

    Returns:
        The validated value (cast to expected_type when possible).

    Raises:
        ConfirmationError: If validation fails.
    """
    # Type check
    if not isinstance(value, expected_type):
        # Try to cast common types
        if expected_type is int and isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ConfirmationError(
                    f"Parameter '{name}' must be an integer, got {value!r}"
                )
        elif expected_type is float and isinstance(value, str):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ConfirmationError(
                    f"Parameter '{name}' must be a number, got {value!r}"
                )
        elif expected_type is bool and isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "y"):
                value = True
            elif value.lower() in ("false", "0", "no", "n"):
                value = False
            else:
                raise ConfirmationError(
                    f"Parameter '{name}' must be a boolean, got {value!r}"
                )
        else:
            raise ConfirmationError(
                f"Parameter '{name}' must be {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    # Range check for numeric types
    if isinstance(value, (int, float)):
        if min_value is not None and value < min_value:
            raise ConfirmationError(
                f"Parameter '{name}' must be >= {min_value}, got {value}"
            )
        if max_value is not None and value > max_value:
            raise ConfirmationError(
                f"Parameter '{name}' must be <= {max_value}, got {value}"
            )

    # Allowed values check
    if allowed_values is not None and value not in allowed_values:
        raise ConfirmationError(
            f"Parameter '{name}' must be one of {allowed_values}, got {value!r}"
        )

    return value


def validate_coordinates(
    coordinate: list | None,
    min_val: int = 0,
    max_val: int = 9999,
) -> list[int] | None:
    """Validate a [x, y] coordinate pair.

    Args:
        coordinate: List of two integers [x, y], or None.
        min_val: Minimum allowed coordinate value.
        max_val: Maximum allowed coordinate value.

    Returns:
        The validated coordinate list, or None if input was None.

    Raises:
        ConfirmationError: If validation fails.
    """
    if coordinate is None:
        return None
    if not isinstance(coordinate, list) or len(coordinate) != 2:
        raise ConfirmationError(
            "Coordinate must be a list of two integers [x, y]"
        )
    x = validate_parameter("x", coordinate[0], int, min_val, max_val)
    y = validate_parameter("y", coordinate[1], int, min_val, max_val)
    return [x, y]