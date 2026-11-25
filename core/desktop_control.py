"""Desktop control for DeskBridge.

Wraps the Hermes computer_use tool (cua-driver) into a clean Python API
so AI agents can control any desktop application through screenshots,
mouse clicks, keyboard input, scrolling, and dragging.

All functions return a dict with keys:
  ok (bool), message (str | None), error (str | None),
  screenshot_path (str | None), element_count (int | None)
"""

import os
import sys

from core.activity_log import record_action


def _log(app_name: str, action: str, args: dict, ok: bool, message: str = "", error: str = None):
    """Record a desktop control action to the activity log."""
    record_action(app_name, action, args, "success" if ok else "failed", message or error or "")


def capture(app: str = None, mode: str = "som") -> dict:
    """Capture a screenshot of the desktop or a specific app.

    Parameters
    ----------
    app : str | None
        Application name to limit capture to. None = frontmost window.
    mode : str
        Capture mode: "som" (numbered overlays), "vision" (plain), or "ax" (accessibility tree).

    Returns
    -------
    dict
        Result with ok, message, screenshot_path, element_count.
    """
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "capture", {"mode": mode}, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {"action": "capture", "mode": mode, "app": app}
    }])
    calls = result.get("calls", [])
    if not calls:
        return {"ok": False, "error": "No response from computer_use", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "capture", {"mode": mode}, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")
    screenshot_path = data.get("screenshot_path")
    element_count = len(data.get("elements", [])) if data.get("elements") else None

    msg = f"Captured screen ({mode})"
    if screenshot_path:
        msg += f": {screenshot_path}"
    if element_count is not None:
        msg += f", {element_count} elements"

    _log(app or "desktop", "capture", {"mode": mode}, True, msg)
    return {
        "ok": True,
        "message": msg,
        "screenshot_path": screenshot_path,
        "element_count": element_count,
        "verdict": verdict,
        "app": app,
    }


def click(element: int = None, coordinate: list = None, app: str = None,
          button: str = "left", modifiers: list = None,
          delivery_mode: str = "background") -> dict:
    """Click an element by SOM index or raw coordinate.

    Parameters
    ----------
    element : int | None
        1-based SOM index from the last capture(mode='som').
    coordinate : list[int] | None
        [x, y] pixel coordinates relative to the captured window.
    app : str | None
        Target application name.
    button : str
        Mouse button: "left", "right", or "middle".
    modifiers : list[str] | None
        Modifier keys held during click.
    delivery_mode : str
        "background" (default) or "foreground".

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {"element": element, "coordinate": coordinate, "app": app, "button": button}
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "click", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "click",
            "element": element,
            "coordinate": coordinate,
            "app": app,
            "button": button,
            "modifiers": modifiers,
            "delivery_mode": delivery_mode,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app or "desktop", "click", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "click", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")
    screenshot_path = data.get("screenshot_path")

    msg = f"Clicked {'element #' + str(element) if element else coordinate} on {app or 'frontmost'}"
    if screenshot_path:
        msg += f" (screenshot: {screenshot_path})"

    _log(app or "desktop", "click", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "screenshot_path": screenshot_path,
        "app": app,
    }


def type_text(text: str, app: str = None, delivery_mode: str = "background") -> dict:
    """Type text into the focused field of the target app.

    Parameters
    ----------
    text : str
        Text to type.
    app : str | None
        Target application name.
    delivery_mode : str
        "background" (default) or "foreground".

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {"text": text, "app": app}
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "type", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "type",
            "text": text,
            "app": app,
            "delivery_mode": delivery_mode,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app or "desktop", "type", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "type", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")

    msg = f"Typed text into {app or 'frontmost app'}"

    _log(app or "desktop", "type", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "app": app,
    }


def press_keys(keys: str, app: str = None, delivery_mode: str = "background") -> dict:
    """Press a key combination.

    Parameters
    ----------
    keys : str
        Key combo, e.g. "cmd+s", "ctrl+alt+t", "return", "escape", "tab".
    app : str | None
        Target application name.
    delivery_mode : str
        "background" (default) or "foreground".

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {"keys": keys, "app": app}
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "key", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "key",
            "keys": keys,
            "app": app,
            "delivery_mode": delivery_mode,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app or "desktop", "key", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "key", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")

    msg = f"Pressed keys '{keys}' on {app or 'frontmost app'}"

    _log(app or "desktop", "key", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "app": app,
    }


def scroll(direction: str, amount: int = 3, app: str = None,
           delivery_mode: str = "background") -> dict:
    """Scroll in the target app.

    Parameters
    ----------
    direction : str
        "up", "down", "left", or "right".
    amount : int
        Scroll wheel ticks (default 3).
    app : str | None
        Target application name.
    delivery_mode : str
        "background" (default) or "foreground".

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {"direction": direction, "amount": amount, "app": app}
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "scroll", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "scroll",
            "direction": direction,
            "amount": amount,
            "app": app,
            "delivery_mode": delivery_mode,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app or "desktop", "scroll", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "scroll", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")

    msg = f"Scrolled {direction} ({amount} ticks) on {app or 'frontmost app'}"

    _log(app or "desktop", "scroll", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "app": app,
    }


def drag(from_element: int = None, from_coordinate: list = None,
         to_element: int = None, to_coordinate: list = None,
         app: str = None, delivery_mode: str = "background") -> dict:
    """Drag from one element/coordinate to another.

    Parameters
    ----------
    from_element : int | None
        Source SOM index.
    from_coordinate : list[int] | None
        Source [x, y].
    to_element : int | None
        Target SOM index.
    to_coordinate : list[int] | None
        Target [x, y].
    app : str | None
        Target application name.
    delivery_mode : str
        "background" (default) or "foreground".

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {
        "from_element": from_element,
        "from_coordinate": from_coordinate,
        "to_element": to_element,
        "to_coordinate": to_coordinate,
        "app": app,
    }
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app or "desktop", "drag", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "drag",
            "from_element": from_element,
            "from_coordinate": from_coordinate,
            "to_element": to_element,
            "to_coordinate": to_coordinate,
            "app": app,
            "delivery_mode": delivery_mode,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app or "desktop", "drag", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app or "desktop", "drag", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")

    msg = f"Dragged on {app or 'frontmost app'}"

    _log(app or "desktop", "drag", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "app": app,
    }


def list_apps() -> dict:
    """List running applications.

    Returns
    -------
    dict
        Result with ok, message, apps (list of app names).
    """
    try:
        from hermes_tools import tool_call
    except ImportError:
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment"}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {"action": "list_apps"}
    }])
    calls = result.get("calls", [])
    if not calls:
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment"}

    call_result = calls[0]
    if call_result.get("error"):
        return {"ok": False, "error": call_result["error"], "message": call_result["error"]}

    data = call_result.get("result", {})
    apps = data.get("apps", [])

    return {"ok": True, "message": f"{len(apps)} applications found", "apps": apps}


def list_windows() -> dict:
    """List open windows.

    Returns
    -------
    dict
        Result with ok, message, windows (list of window descriptors).
    """
    try:
        from hermes_tools import tool_call
    except ImportError:
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment"}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {"action": "list_windows"}
    }])
    calls = result.get("calls", [])
    if not calls:
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment"}

    call_result = calls[0]
    if call_result.get("error"):
        return {"ok": False, "error": call_result["error"], "message": call_result["error"]}

    data = call_result.get("result", {})
    windows = data.get("windows", [])

    return {"ok": True, "message": f"{len(windows)} windows found", "windows": windows}


def focus_app(app: str, raise_window: bool = False) -> dict:
    """Focus (bring input focus to) an application.

    Parameters
    ----------
    app : str
        Application name.
    raise_window : bool
        If True, brings window to front (disruptive). Default False.

    Returns
    -------
    dict
        Result with ok, message, verdict.
    """
    args = {"app": app, "raise_window": raise_window}
    try:
        from hermes_tools import tool_call
    except ImportError:
        _log(app, "focus_app", args, False, "", "computer_use tool only available within Hermes agent context")
        return {"ok": False, "error": "computer_use tool only available within Hermes agent context", "message": "Desktop control requires the Hermes agent environment", "app": app}

    result = tool_call([{
        "name": "computer_use",
        "arguments": {
            "action": "focus_app",
            "app": app,
            "raise_window": raise_window,
        }
    }])
    calls = result.get("calls", [])
    if not calls:
        _log(app, "focus_app", args, False, "", "No response from computer_use")
        return {"ok": False, "error": "No response from computer_use", "message": "Desktop control requires the Hermes agent environment", "app": app}

    call_result = calls[0]
    if call_result.get("error"):
        _log(app, "focus_app", args, False, "", call_result["error"])
        return {"ok": False, "error": call_result["error"], "message": call_result["error"], "app": app}

    data = call_result.get("result", {})
    verdict = data.get("verdict", "")

    msg = f"Focused app: {app}"

    _log(app, "focus_app", args, True, msg)
    return {
        "ok": True,
        "message": msg,
        "verdict": verdict,
        "app": app,
    }