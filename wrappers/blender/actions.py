"""Actual actions for the Blender wrapper."""

import os
import subprocess


def render_scene(file_path: str, output_path: str) -> dict:
    """Render a Blender file using Blender headless mode.

    Returns a dictionary with key 'ok' (bool) and 'message' or 'error'.
    """
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"Blender file not found: {file_path}"}

    # Blender headless command for rendering
    cmd = [
        "blender",
        "--background",
        file_path,
        "--render-output",
        output_path,
        "--render-animation",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        if result.returncode == 0:
            return {
                "ok": True,
                "message": f"Render complete: {output_path}",
                "stdout": result.stdout,
            }
        return {
            "ok": False,
            "error": f"Blender failed (code {result.returncode})",
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "Blender is not installed or not in PATH",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "Render exceeded time limit (300 seconds)",
        }