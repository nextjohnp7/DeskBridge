"""Desktop control for DeskBridge.

Wraps desktop automation backends into a clean Python API so AI agents can
control any desktop application through screenshots, mouse clicks, keyboard
input, scrolling, and dragging.

Architecture: pluggable backends.  The Hermes ``computer_use`` tool (cua-driver)
is one backend; additional backends (MCP, Claude Desktop, pyautogui, etc.) can
be added by subclassing :class:`DesktopBackend` and registering them with
:class:`DesktopController`.

All functions return a dict with keys:
  ok (bool), message (str | None), error (str | None),
  screenshot_path (str | None), element_count (int | None)
"""

from __future__ import annotations

import abc
import os
import sys
from typing import Any

from core.activity_log import record_action


class DesktopBackend(abc.ABC):
    """Abstract base class for desktop automation backends.

    Subclasses implement the concrete automation mechanism (Hermes computer_use,
    MCP server, pyautogui, etc.).
    """

    name: str = "base"

    @abc.abstractmethod
    def capture(self, app: str | None = None, mode: str = "som") -> dict:
        """Capture a screenshot of the desktop or a specific app."""
        raise NotImplementedError

    @abc.abstractmethod
    def click(
        self,
        element: int | None = None,
        coordinate: list[int] | None = None,
        app: str | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        """Click an element by SOM index or raw coordinate."""
        raise NotImplementedError

    @abc.abstractmethod
    def type_text(
        self, text: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        """Type text into the focused field of the target app."""
        raise NotImplementedError

    @abc.abstractmethod
    def press_keys(
        self, keys: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        """Press a key combination."""
        raise NotImplementedError

    @abc.abstractmethod
    def scroll(
        self,
        direction: str,
        amount: int = 3,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        """Scroll in the target app."""
        raise NotImplementedError

    @abc.abstractmethod
    def drag(
        self,
        from_element: int | None = None,
        from_coordinate: list[int] | None = None,
        to_element: int | None = None,
        to_coordinate: list[int] | None = None,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        """Drag from one element/coordinate to another."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_apps(self) -> dict:
        """List running applications."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_windows(self) -> dict:
        """List open windows."""
        raise NotImplementedError

    @abc.abstractmethod
    def focus_app(self, app: str, raise_window: bool = False) -> dict:
        """Focus (bring input focus to) an application."""
        raise NotImplementedError


class HermesComputerUseBackend(DesktopBackend):
    """Backend that wraps the Hermes ``computer_use`` tool (cua-driver).

    Only available within the Hermes agent context via ``tool_call``.  Outside
    that context every method returns ``ok=False`` with a clear error message
    explaining the environment constraint.
    """

    name = "hermes_computer_use"

    def _call(self, arguments: dict) -> dict:
        """Invoke the Hermes ``computer_use`` tool.

        Returns a dict with ``ok``, ``message`` or ``error`` keys.
        """
        try:
            from hermes_tools import tool_call
        except ImportError:
            return {
                "ok": False,
                "error": "hermes_tools not available",
                "message": "Desktop control requires the Hermes agent environment",
            }

        result = tool_call([{"name": "computer_use", "arguments": arguments}])
        calls = result.get("calls", [])
        if not calls:
            return {
                "ok": False,
                "error": "No response from computer_use",
                "message": "Desktop control requires the Hermes agent environment",
            }

        call_result = calls[0]
        if call_result.get("error"):
            return {
                "ok": False,
                "error": call_result["error"],
                "message": call_result["error"],
            }

        return {"ok": True, "result": call_result.get("result", {})}

    def capture(self, app: str | None = None, mode: str = "som") -> dict:
        call = self._call({"action": "capture", "mode": mode, "app": app})
        if not call["ok"]:
            return call
        data = call["result"]
        screenshot_path = data.get("screenshot_path")
        element_count = len(data.get("elements", [])) if data.get("elements") else None
        msg = f"Captured screen ({mode})"
        if screenshot_path:
            msg += f": {screenshot_path}"
        if element_count is not None:
            msg += f", {element_count} elements"
        return {
            "ok": True,
            "message": msg,
            "screenshot_path": screenshot_path,
            "element_count": element_count,
            "verdict": data.get("verdict", ""),
            "app": app,
        }

    def click(
        self,
        element: int | None = None,
        coordinate: list[int] | None = None,
        app: str | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        call = self._call(
            {
                "action": "click",
                "element": element,
                "coordinate": coordinate,
                "app": app,
                "button": button,
                "modifiers": modifiers,
                "delivery_mode": delivery_mode,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        screenshot_path = data.get("screenshot_path")
        target = f"element #{element}" if element else f"coordinate {coordinate}"
        msg = f"Clicked {target} on {app or 'frontmost'}"
        if screenshot_path:
            msg += f" (screenshot: {screenshot_path})"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "screenshot_path": screenshot_path,
            "app": app,
        }

    def type_text(
        self, text: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        call = self._call(
            {
                "action": "type",
                "text": text,
                "app": app,
                "delivery_mode": delivery_mode,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        msg = f"Typed text into {app or 'frontmost app'}"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "app": app,
        }

    def press_keys(
        self, keys: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        call = self._call(
            {
                "action": "key",
                "keys": keys,
                "app": app,
                "delivery_mode": delivery_mode,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        msg = f"Pressed keys '{keys}' on {app or 'frontmost app'}"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "app": app,
        }

    def scroll(
        self,
        direction: str,
        amount: int = 3,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        call = self._call(
            {
                "action": "scroll",
                "direction": direction,
                "amount": amount,
                "app": app,
                "delivery_mode": delivery_mode,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        msg = f"Scrolled {direction} ({amount} ticks) on {app or 'frontmost app'}"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "app": app,
        }

    def drag(
        self,
        from_element: int | None = None,
        from_coordinate: list[int] | None = None,
        to_element: int | None = None,
        to_coordinate: list[int] | None = None,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        call = self._call(
            {
                "action": "drag",
                "from_element": from_element,
                "from_coordinate": from_coordinate,
                "to_element": to_element,
                "to_coordinate": to_coordinate,
                "app": app,
                "delivery_mode": delivery_mode,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        msg = f"Dragged on {app or 'frontmost app'}"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "app": app,
        }

    def list_apps(self) -> dict:
        call = self._call({"action": "list_apps"})
        if not call["ok"]:
            return call
        data = call["result"]
        apps = data.get("apps", [])
        return {
            "ok": True,
            "message": f"{len(apps)} applications found",
            "apps": apps,
        }

    def list_windows(self) -> dict:
        call = self._call({"action": "list_windows"})
        if not call["ok"]:
            return call
        data = call["result"]
        windows = data.get("windows", [])
        return {
            "ok": True,
            "message": f"{len(windows)} windows found",
            "windows": windows,
        }

    def focus_app(self, app: str, raise_window: bool = False) -> dict:
        call = self._call(
            {
                "action": "focus_app",
                "app": app,
                "raise_window": raise_window,
            }
        )
        if not call["ok"]:
            return call
        data = call["result"]
        msg = f"Focused app: {app}"
        return {
            "ok": True,
            "message": msg,
            "verdict": data.get("verdict", ""),
            "app": app,
        }


class PyAutoGUIBackend(DesktopBackend):
    """Backend that wraps the PyAutoGUI Python package.

    Available cross-platform without requiring the Hermes agent context.
    Requires: pip install pyautogui
    """

    name = "pyautogui"

    def _require_pyautogui(self) -> dict:
        try:
            import pyautogui  # noqa: F401
        except ImportError:
            return {
                "ok": False,
                "error": "pyautogui not installed",
                "message": "Install pyautogui to use the PyAutoGUI backend",
            }
        return {"ok": True}

    def capture(self, app: str | None = None, mode: str = "som") -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            import tempfile
            screenshot = pyautogui.screenshot()
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=os.getcwd())
            screenshot.save(tmp.name)
            return {
                "ok": True,
                "message": f"Captured screenshot: {tmp.name}",
                "screenshot_path": tmp.name,
                "element_count": None,
                "app": app,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def click(
        self,
        element: int | None = None,
        coordinate: list[int] | None = None,
        app: str | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            if coordinate:
                x, y = coordinate
                pyautogui.click(x=x, y=y, button=button)
                return {"ok": True, "message": f"Clicked at {coordinate}", "app": app}
            return {
                "ok": False,
                "error": "PyAutoGUI backend requires --coordinate, not --element",
                "app": app,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def type_text(
        self, text: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            pyautogui.write(text)
            return {"ok": True, "message": "Typed text", "app": app}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def press_keys(
        self, keys: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            key_list = keys.replace("cmd", "command").split("+")
            pyautogui.hotkey(*key_list)
            return {"ok": True, "message": f"Pressed keys: {keys}", "app": app}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def scroll(
        self,
        direction: str,
        amount: int = 3,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            scroll_amount = amount if direction == "up" else -amount
            pyautogui.scroll(scroll_amount)
            return {
                "ok": True,
                "message": f"Scrolled {direction} ({amount} ticks)",
                "app": app,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def drag(
        self,
        from_element: int | None = None,
        from_coordinate: list[int] | None = None,
        to_element: int | None = None,
        to_coordinate: list[int] | None = None,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            if from_coordinate and to_coordinate:
                x1, y1 = from_coordinate
                x2, y2 = to_coordinate
                pyautogui.moveTo(x1, y1)
                pyautogui.dragTo(x2, y2, button="left")
                return {"ok": True, "message": "Dragged", "app": app}
            return {
                "ok": False,
                "error": "PyAutoGUI backend requires --from-coordinate and --to-coordinate",
                "app": app,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "app": app}

    def list_apps(self) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            active = pyautogui.getActiveWindowTitle()
            return {
                "ok": True,
                "message": f"Active window: {active or 'unknown'}",
                "apps": [active] if active else [],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def list_windows(self) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        try:
            import pyautogui
            active = pyautogui.getActiveWindowTitle()
            return {
                "ok": True,
                "message": f"Active window: {active or 'unknown'}",
                "windows": [active] if active else [],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def focus_app(self, app: str, raise_window: bool = False) -> dict:
        check = self._require_pyautogui()
        if not check["ok"]:
            return check
        return {
            "ok": False,
            "error": "focus_app not supported by PyAutoGUI backend",
            "app": app,
        }


class DesktopController:
    """Manages desktop backends and routes calls to the first available one."""

    def __init__(self) -> None:
        self.backends: list[DesktopBackend] = []
        self.active: DesktopBackend | None = None
        self._discover()

    def _discover(self) -> None:
        """Auto-detect available backends.

        Order matters: prefer Hermes computer_use when running inside the
        Hermes agent; fall back to PyAutoGUI when installed.
        """
        try:
            from hermes_tools import tool_call  # noqa: F401  (availability check)

            self.backends.append(HermesComputerUseBackend())
        except ImportError:
            pass

        try:
            import pyautogui  # noqa: F401  (availability check)

            self.backends.append(PyAutoGUIBackend())
        except ImportError:
            pass

        if self.backends:
            self.active = self.backends[0]

    def register(self, backend: DesktopBackend) -> None:
        """Register an additional backend (e.g. MCP, Claude Desktop)."""
        self.backends.append(backend)
        if self.active is None:
            self.active = backend

    def _backend_error(
        self, app_name: str | None, action: str, args: dict
    ) -> dict:
        """Record and return an error when no backend is available."""
        record_action(
            app_name or "desktop",
            action,
            args,
            "failed",
            "No desktop backend available",
        )
        return {
            "ok": False,
            "error": "No desktop backend available",
            "message": (
                "No desktop backend is available. Install Hermes Agent (for the "
                "computer_use backend) or install pyautogui (for the PyAutoGUI "
                "backend), or register a custom DesktopBackend subclass."
            ),
            "app": app_name,
        }

    def _get_backend(
        self, app_name: str | None, action: str, args: dict
    ) -> DesktopBackend | None:
        """Return the active backend, or an error dict if none is available."""
        if self.active is None:
            return None  # caller handles via _backend_error
        return self.active

    # --- Public API (delegates to active backend) ---

    def capture(self, app: str | None = None, mode: str = "som") -> dict:
        backend = self._get_backend(app, "capture", {"mode": mode})
        if backend is None:
            return self._backend_error(app, "capture", {"mode": mode})
        result = backend.capture(app=app, mode=mode)
        record_action(
            app or "desktop", "capture", {"mode": mode},
            result["ok"], result.get("message", ""),
        )
        return result

    def click(
        self,
        element: int | None = None,
        coordinate: list[int] | None = None,
        app: str | None = None,
        button: str = "left",
        modifiers: list[str] | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        args = {
            "element": element,
            "coordinate": coordinate,
            "app": app,
            "button": button,
        }
        backend = self._get_backend(app, "click", args)
        if backend is None:
            return self._backend_error(app, "click", args)
        result = backend.click(
            element=element,
            coordinate=coordinate,
            app=app,
            button=button,
            modifiers=modifiers,
            delivery_mode=delivery_mode,
        )
        record_action(
            app or "desktop", "click", args,
            result["ok"], result.get("message", ""),
        )
        return result

    def type_text(
        self, text: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        args = {"text": text, "app": app}
        backend = self._get_backend(app, "type", args)
        if backend is None:
            return self._backend_error(app, "type", args)
        result = backend.type_text(text=text, app=app, delivery_mode=delivery_mode)
        record_action(
            app or "desktop", "type", args,
            result["ok"], result.get("message", ""),
        )
        return result

    def press_keys(
        self, keys: str, app: str | None = None, delivery_mode: str = "background"
    ) -> dict:
        args = {"keys": keys, "app": app}
        backend = self._get_backend(app, "key", args)
        if backend is None:
            return self._backend_error(app, "key", args)
        result = backend.press_keys(keys=keys, app=app, delivery_mode=delivery_mode)
        record_action(
            app or "desktop", "key", args,
            result["ok"], result.get("message", ""),
        )
        return result

    def scroll(
        self,
        direction: str,
        amount: int = 3,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        args = {"direction": direction, "amount": amount, "app": app}
        backend = self._get_backend(app, "scroll", args)
        if backend is None:
            return self._backend_error(app, "scroll", args)
        result = backend.scroll(
            direction=direction, amount=amount, app=app,
            delivery_mode=delivery_mode,
        )
        record_action(
            app or "desktop", "scroll", args,
            result["ok"], result.get("message", ""),
        )
        return result

    def drag(
        self,
        from_element: int | None = None,
        from_coordinate: list[int] | None = None,
        to_element: int | None = None,
        to_coordinate: list[int] | None = None,
        app: str | None = None,
        delivery_mode: str = "background",
    ) -> dict:
        args = {
            "from_element": from_element,
            "from_coordinate": from_coordinate,
            "to_element": to_element,
            "to_coordinate": to_coordinate,
            "app": app,
        }
        backend = self._get_backend(app, "drag", args)
        if backend is None:
            return self._backend_error(app, "drag", args)
        result = backend.drag(
            from_element=from_element,
            from_coordinate=from_coordinate,
            to_element=to_element,
            to_coordinate=to_coordinate,
            app=app,
            delivery_mode=delivery_mode,
        )
        record_action(
            app or "desktop", "drag", args,
            result["ok"], result.get("message", ""),
        )
        return result

    def list_apps(self) -> dict:
        backend = self._get_backend("desktop", "list_apps", {})
        if backend is None:
            return self._backend_error("desktop", "list_apps", {})
        return backend.list_apps()

    def list_windows(self) -> dict:
        backend = self._get_backend("desktop", "list_windows", {})
        if backend is None:
            return self._backend_error("desktop", "list_windows", {})
        return backend.list_windows()

    def focus_app(self, app: str, raise_window: bool = False) -> dict:
        args = {"app": app, "raise_window": raise_window}
        backend = self._get_backend(app, "focus_app", args)
        if backend is None:
            return self._backend_error(app, "focus_app", args)
        result = backend.focus_app(app=app, raise_window=raise_window)
        record_action(
            app, "focus_app", args,
            result["ok"], result.get("message", ""),
        )
        return result


# Module-level singleton controller
controller = DesktopController()


# Module-level convenience functions (stable API for callers)
def capture(app: str | None = None, mode: str = "som") -> dict:
    return controller.capture(app=app, mode=mode)


def click(
    element: int | None = None,
    coordinate: list[int] | None = None,
    app: str | None = None,
    button: str = "left",
    modifiers: list[str] | None = None,
    delivery_mode: str = "background",
) -> dict:
    return controller.click(
        element=element,
        coordinate=coordinate,
        app=app,
        button=button,
        modifiers=modifiers,
        delivery_mode=delivery_mode,
    )


def type_text(
    text: str, app: str | None = None, delivery_mode: str = "background"
) -> dict:
    return controller.type_text(text=text, app=app, delivery_mode=delivery_mode)


def press_keys(
    keys: str, app: str | None = None, delivery_mode: str = "background"
) -> dict:
    return controller.press_keys(keys=keys, app=app, delivery_mode=delivery_mode)


def scroll(
    direction: str, amount: int = 3, app: str | None = None,
    delivery_mode: str = "background",
) -> dict:
    return controller.scroll(
        direction=direction, amount=amount, app=app,
        delivery_mode=delivery_mode,
    )


def drag(
    from_element: int | None = None,
    from_coordinate: list[int] | None = None,
    to_element: int | None = None,
    to_coordinate: list[int] | None = None,
    app: str | None = None,
    delivery_mode: str = "background",
) -> dict:
    return controller.drag(
        from_element=from_element,
        from_coordinate=from_coordinate,
        to_element=to_element,
        to_coordinate=to_coordinate,
        app=app,
        delivery_mode=delivery_mode,
    )


def list_apps() -> dict:
    return controller.list_apps()


def list_windows() -> dict:
    return controller.list_windows()


def focus_app(app: str, raise_window: bool = False) -> dict:
    return controller.focus_app(app=app, raise_window=raise_window)


def register_backend(backend: DesktopBackend) -> None:
    """Register a custom desktop backend (e.g. MCP, Claude Desktop)."""
    controller.register(backend)


def list_backends() -> list[str]:
    """Return names of all registered backends."""
    return [b.name for b in controller.backends]


def active_backend() -> str | None:
    """Return the name of the active backend, or None if none available."""
    return controller.active.name if controller.active else None