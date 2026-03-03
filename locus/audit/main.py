"""locus-audit CLI entrypoint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .model import AuditResult, AuditSummary, RoomResult
from .scanner import (
    collect_room_signals,
    compute_global_feedback,
    discover_rooms,
    enrich_with_metrics,
    load_metrics,
    score_room,
)
from .report import render_markdown, write_reports


def run_audit(palace_path: Path, room_filter: str | None = None) -> AuditResult:
    palace_path = palace_path.resolve()
    audited_at = datetime.now(timezone.utc).isoformat()

    index = palace_path / "INDEX.md"
    index_lines = sum(1 for _ in index.open("r", errors="replace")) if index.exists() else 0

    runs = load_metrics(palace_path)

    room_dirs, unstructured = discover_rooms(palace_path)
    if room_filter:
        room_dirs = [r for r in room_dirs if room_filter in str(r)]

    rooms: list[RoomResult] = []
    for room_dir in sorted(room_dirs):
        signals = collect_room_signals(room_dir)
        enrich_with_metrics(room_dir, palace_path, signals, runs)
        status, actions = score_room(signals)
        rooms.append(RoomResult(
            path=str(room_dir.relative_to(palace_path)),
            status=status,
            signals=signals,
            actions=actions,
        ))

    summary = AuditSummary(
        total_rooms=len(rooms),
        critical=sum(1 for r in rooms if r.status == "critical"),
        degraded=sum(1 for r in rooms if r.status == "degraded"),
        stale=sum(1 for r in rooms if r.status == "stale"),
        healthy=sum(1 for r in rooms if r.status == "healthy"),
        unstructured_dirs=unstructured,
        metrics_runs_analysed=len(runs),
    )
    summary.global_pass_rate, summary.global_fail_rate = compute_global_feedback(runs)

    # Build prioritised action items (critical first, then degraded)
    action_items = []
    priority = 1
    for status in ("critical", "degraded", "stale"):
        for room in rooms:
            if room.status == status:
                for action in room.actions:
                    action_items.append({
                        "priority": priority,
                        "status": status,
                        "room": room.path,
                        "action": action,
                    })
                    priority += 1

    # INDEX.md oversize action
    if index_lines > 50:
        action_items.append({
            "priority": priority,
            "status": "warning",
            "room": "INDEX.md",
            "action": f"Trim INDEX.md — {index_lines} lines exceeds 50-line limit",
        })

    return AuditResult(
        audited_at=audited_at,
        palace_path=str(palace_path),
        index_lines=index_lines,
        rooms=rooms,
        summary=summary,
        action_items=action_items,
        has_metrics=bool(runs),
    )


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="locus-audit",
        description="Audit a Locus memory palace and generate a health report.",
    )
    parser.add_argument(
        "--palace",
        required=True,
        type=Path,
        help="Path to the palace root directory.",
    )
    parser.add_argument(
        "--room",
        default=None,
        help="Scope audit to a single room path (substring match).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Print JSON report to stdout instead of markdown.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print report without writing to _metrics/.",
    )

    args = parser.parse_args()

    result = run_audit(args.palace, room_filter=args.room)

    if args.output_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(render_markdown(result))

    if not args.no_write:
        md_path, json_path = write_reports(result, args.palace.resolve())
        print(f"\nReports written:")
        print(f"  {md_path}")
        print(f"  {json_path}")


if __name__ == "__main__":
    cli()
