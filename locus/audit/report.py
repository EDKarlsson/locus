"""Report renderer — produces markdown and JSON output from AuditResult."""

from __future__ import annotations

import json
from pathlib import Path

from .model import AuditResult, RoomResult

_STATUS_ICON = {
    "critical": "🔴",
    "degraded": "🟡",
    "stale": "⚪",
    "healthy": "✅",
}

_SIGNAL_THRESHOLDS = {
    "main_lines":           (200, 150),   # (critical, warn)
    "max_specialty_lines":  (300, None),
    "session_log_count":    (None, 5),
    "oldest_session_days":  (None, 30),
    "retrieval_depth_avg":  (None, 3.5),
    "feedback_fail_rate":   (0.3, 0.15),
}


def _signal_icon(key: str, value: float | int | None) -> str:
    if value is None:
        return "—"
    crit, warn = _SIGNAL_THRESHOLDS.get(key, (None, None))
    if crit is not None and value > crit:
        return "❌"
    if warn is not None and value > warn:
        return "⚠️"
    return "✅"


def render_room(room: RoomResult) -> str:
    icon = _STATUS_ICON.get(room.status, "?")
    s = room.signals
    lines = [
        f"### `{room.path}` {icon} {room.status}",
        "",
        "| Signal | Value | Status |",
        "|---|---|---|",
    ]

    signal_rows = [
        ("main_lines", s.main_lines),
        ("specialty_files", s.specialty_files),
        ("max_specialty_lines", s.max_specialty_lines),
        ("session_log_count", s.session_log_count),
        ("oldest_session_days", f"{s.oldest_session_days:.1f} days" if s.oldest_session_days is not None else None),
        ("retrieval_depth_avg", f"{s.retrieval_depth_avg:.1f}" if s.retrieval_depth_avg is not None else None),
        ("feedback_pass_rate", f"{s.feedback_pass_rate:.0%}" if s.feedback_pass_rate is not None else None),
        ("feedback_fail_rate", f"{s.feedback_fail_rate:.0%}" if s.feedback_fail_rate is not None else None),
    ]

    for key, val in signal_rows:
        raw = getattr(s, key, None)
        icon_cell = _signal_icon(key, raw if isinstance(raw, (int, float)) else None)
        lines.append(f"| {key} | {val if val is not None else '—'} | {icon_cell} |")

    if room.actions:
        lines += ["", "**Actions:**"]
        for action in room.actions:
            lines.append(f"- {action}")

    lines.append("")
    return "\n".join(lines)


def render_markdown(result: AuditResult) -> str:
    s = result.summary
    status_summary = (
        f"{s.total_rooms} total — "
        f"{s.critical} critical, {s.degraded} degraded, "
        f"{s.stale} stale, {s.healthy} healthy"
    )

    index_icon = "✅" if result.index_lines <= 50 else "⚠️"
    pass_str = f"{s.global_pass_rate:.0%}" if s.global_pass_rate is not None else "—"
    fail_str = f"{s.global_fail_rate:.0%}" if s.global_fail_rate is not None else "—"

    lines = [
        "# Palace Health Report",
        "",
        f"Audited: {result.audited_at}",
        f"Palace: {result.palace_path}",
        f"Rooms: {status_summary}",
    ]

    if not result.has_metrics:
        lines += [
            "",
            "> **Note:** no `_metrics/` data found — retrieval and feedback signals skipped.",
            "> Run at least one `locus` query to enable full health analysis.",
        ]

    lines += [
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| INDEX.md lines | {result.index_lines} / 50 ({index_icon}) |",
        f"| Total rooms | {s.total_rooms} |",
        f"| Critical | {s.critical} |",
        f"| Degraded | {s.degraded} |",
        f"| Stale | {s.stale} |",
        f"| Healthy | {s.healthy} |",
        f"| Unstructured dirs | {s.unstructured_dirs} |",
        f"| Metrics runs analysed | {s.metrics_runs_analysed} |",
        f"| Global pass rate | {pass_str} |",
        f"| Global fail rate | {fail_str} |",
    ]

    if result.action_items:
        lines += ["", "---", "", "## Action Items", "", "Priority-ordered. Address critical items before degraded.", ""]
        for item in result.action_items:
            icon = _STATUS_ICON.get(item.get("status", ""), "·")
            lines.append(
                f"{item['priority']}. {icon} **[{item['status']}]** "
                f"`{item['room']}` — {item['action']}"
            )

    lines += ["", "---", "", "## Per-Room Detail", ""]
    for room in sorted(result.rooms, key=lambda r: ("healthy", "stale", "degraded", "critical").index(r.status) if r.status in ("healthy", "stale", "degraded", "critical") else 0, reverse=True):
        lines.append(render_room(room))

    return "\n".join(lines)


def write_reports(result: AuditResult, palace_root: Path) -> tuple[Path, Path]:
    """Write markdown + JSON reports to palace/_metrics/. Return (md_path, json_path)."""
    metrics_dir = palace_root / "_metrics"
    metrics_dir.mkdir(exist_ok=True)

    # Produce audit-YYYY-MM-DDTHHMMSSZ per spec/health-report-format.md
    # Keep date dashes, remove time colons only.
    ts = result.audited_at[:19].replace(":", "") + "Z"
    stem = f"audit-{ts}"

    md_path = metrics_dir / f"{stem}.md"
    json_path = metrics_dir / f"{stem}.json"
    last_audit = metrics_dir / "_last-audit.txt"

    md_path.write_text(render_markdown(result))
    json_path.write_text(json.dumps(result.to_dict(), indent=2))
    last_audit.write_text(result.audited_at + "\n")

    return md_path, json_path
