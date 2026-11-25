"""Actual actions for the GIMP wrapper."""

import os
import subprocess


def export_image(input_path: str, output_path: str) -> dict:
    """Export a GIMP image to an output file using GIMP batch mode.

    Returns a dictionary with key 'ok' (bool) and 'message' or 'error'.
    """
    if not os.path.exists(input_path):
        return {"ok": False, "error": f"Input file not found: {input_path}"}

    script = (
        '(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE "'
        + input_path + '" "' + input_path + '")))'
        + ' (drawable (car (gimp-image-get-active-layer image))))'
        + ' (gimp-file-save RUN-NONINTERACTIVE image drawable "'
        + output_path + '" "' + output_path + '"))'
        + ' (gimp-quit 0))'
    )

    cmd = [
        "gimp",
        "-i",
        "-b",
        script,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return {
                "ok": True,
                "message": f"Export complete: {output_path}",
                "stdout": result.stdout,
            }
        return {
            "ok": False,
            "error": f"GIMP failed (code {result.returncode})",
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "GIMP is not installed or not in PATH",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "Export exceeded time limit (120 seconds)",
        }