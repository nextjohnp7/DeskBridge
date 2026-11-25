"""Chart generator for DeskBridge activity logs.

Creates an SVG bar chart showing action success/failure counts per wrapper
using only the Python standard library.
"""

import os
from xml.sax.saxutils import escape

from core.activity_log import read_logs


REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")


def ensure_report_dir():
    """Create the reports directory if it does not exist."""
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR, exist_ok=True)


def generate_chart(output_path: str = None) -> str:
    """Generate an SVG chart of activity log statistics.

    Parameters
    ----------
    output_path : str | None
        Path to save the SVG file. If None, saves to reports/activity_chart.svg.

    Returns
    -------
    str
        Path to the generated SVG file.
    """
    ensure_report_dir()
    if output_path is None:
        output_path = os.path.join(REPORT_DIR, "activity_chart.svg")

    logs = read_logs()

    # Count success/failure per app
    app_stats = {}
    for entry in logs:
        app = entry["app"]
        status = entry["status"]
        if app not in app_stats:
            app_stats[app] = {"success": 0, "failed": 0}
        app_stats[app][status] += 1

    apps = sorted(app_stats.keys())
    success_counts = [app_stats[a]["success"] for a in apps]
    failure_counts = [app_stats[a]["failed"] for a in apps]

    # SVG layout constants
    width = 600
    height = 400
    margin_left = 80
    margin_bottom = 60
    margin_top = 40
    margin_right = 40
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    max_value = max(max(success_counts, default=0), max(failure_counts, default=0), 1)
    bar_width = chart_width / (len(apps) * 3) if apps else 20

    lines = []
    lines.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
    lines.append(f'<rect width="{width}" height="{height}" fill="#f9fafb"/>')

    # Title
    lines.append(
        f'<text x="{width // 2}" y="25" text-anchor="middle" font-size="16" '
        f'font-family="sans-serif" fill="#1f2937">DeskBridge Activity Log Chart</text>'
    )
    lines.append(
        f'<text x="{width // 2}" y="45" text-anchor="middle" font-size="12" '
        f'font-family="sans-serif" fill="#6b7280">Blue = Success, Red = Failed</text>'
    )

    # Draw bars
    for i, app in enumerate(apps):
        x_base = margin_left + i * (chart_width / len(apps))
        success = success_counts[i]
        failure = failure_counts[i]

        success_height = (success / max_value) * chart_height if max_value > 0 else 0
        failure_height = (failure / max_value) * chart_height if max_value > 0 else 0

        success_y = height - margin_bottom - success_height
        failure_y = height - margin_bottom - failure_height

        # Success bar (blue)
        lines.append(
            f'<rect x="{x_base + 5}" y="{success_y}" width="{bar_width}" '
            f'height="{success_height}" fill="#2563eb"/>'
        )
        # Failure bar (red)
        lines.append(
            f'<rect x="{x_base + 5 + bar_width}" y="{failure_y}" width="{bar_width}" '
            f'height="{failure_height}" fill="#ef4444"/>'
        )

        # App name label
        lines.append(
            f'<text x="{x_base + bar_width + 10}" y="{height - margin_bottom + 20}" '
            f'text-anchor="middle" font-size="11" font-family="sans-serif" fill="#1f2937">'
            f'{escape(app)}</text>'
        )

        # Value labels on bars
        if success > 0:
            lines.append(
                f'<text x="{x_base + 5 + bar_width / 2}" y="{success_y - 5}" '
                f'text-anchor="middle" font-size="10" font-family="sans-serif" fill="#2563eb">{success}</text>'
            )
        if failure > 0:
            lines.append(
                f'<text x="{x_base + 5 + bar_width + bar_width / 2}" y="{failure_y - 5}" '
                f'text-anchor="middle" font-size="10" font-family="sans-serif" fill="#ef4444">{failure}</text>'
            )

    # Y-axis labels
    for i in range(max_value + 1):
        y = height - margin_bottom - (i / max_value) * chart_height
        lines.append(
            f'<text x="{margin_left - 10}" y="{y + 4}" text-anchor="end" font-size="10" '
            f'font-family="sans-serif" fill="#6b7280">{i}</text>'
        )

    # Legend
    legend_y = margin_top
    lines.append(
        f'<rect x="{width - margin_right - 100}" y="{legend_y}" width="12" height="12" fill="#2563eb"/>'
    )
    lines.append(
        f'<text x="{width - margin_right - 85}" y="{legend_y + 10}" font-size="11" '
        f'font-family="sans-serif" fill="#1f2937">Success</text>'
    )
    lines.append(
        f'<rect x="{width - margin_right - 100}" y="{legend_y + 20}" width="12" height="12" fill="#ef4444"/>'
    )
    lines.append(
        f'<text x="{width - margin_right - 85}" y="{legend_y + 30}" font-size="11" '
        f'font-family="sans-serif" fill="#1f2937">Failed</text>'
    )

    lines.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path