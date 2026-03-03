"""Palace scanner — collects per-room signals from files and _metrics/.

Algorithm defined in spec/audit-algorithm.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .model import RoomSignals, RoomResult, AuditSummary


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", errors="replace"))
    except OSError:
        return 0


def _days_ago(path: Path) -> float:
    try:
        mtime = path.stat().st_mtime
        age = datetime.now(timezone.utc).timestamp() - mtime
        return age / 86400
    except OSError:
        return 0.0


def discover_rooms(palace_root: Path) -> tuple[list[Path], int]:
    """Return (room_dirs, unstructured_count).

    A room dir contains a <dirname>.md main file.
    _metrics/ and sessions/ are excluded from discovery.
    """
    rooms: list[Path] = []
    unstructured = 0

    skip = {"_metrics", "sessions", "archived"}

    for d in palace_root.rglob("*/"):
        if any(part in skip for part in d.parts):
            continue
        if d == palace_root:
            continue
        main = d / f"{d.name}.md"
        if main.exists():
            rooms.append(d)
        elif any(d.glob("*.md")):
            unstructured += 1

    return rooms, unstructured


def collect_room_signals(room_dir: Path) -> RoomSignals:
    sig = RoomSignals()
    main = room_dir / f"{room_dir.name}.md"

    sig.main_lines = _count_lines(main) if main.exists() else 0

    specialty = [
        f for f in room_dir.glob("*.md")
        if f != main and f.name != "sessions"
    ]
    sig.specialty_files = len(specialty)
    sig.max_specialty_lines = max((_count_lines(f) for f in specialty), default=0)

    sessions_dir = room_dir / "sessions"
    if sessions_dir.exists():
        archived = sessions_dir / "archived"
        logs = [f for f in sessions_dir.glob("*.md")
                if not (archived.exists() and f.is_relative_to(archived))]
        sig.session_log_count = len(logs)
        if logs:
            sig.oldest_session_days = max(_days_ago(f) for f in logs)

    return sig


def load_metrics(palace_root: Path) -> list[dict]:
    metrics_dir = palace_root / "_metrics"
    if not metrics_dir.exists():
        return []
    runs = []
    for f in metrics_dir.glob("*.json"):
        if f.name.startswith("audit-"):
            continue
        try:
            data = json.loads(f.read_text())
            if isinstance(data, dict):
                runs.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return runs


def enrich_with_metrics(
    room_dir: Path,
    palace_root: Path,
    signals: RoomSignals,
    runs: list[dict],
) -> None:
    """Populate retrieval/feedback signals from metrics runs."""
    rel = str(room_dir.relative_to(palace_root))

    touching = [
        r for r in runs
        if any(
            fr.get("path", "").startswith(rel)
            for fr in r.get("files_read", [])
        )
    ]
    if not touching:
        return

    depths = [r["retrieval_depth"] for r in touching if "retrieval_depth" in r]
    lines = [r["total_lines"] for r in touching if "total_lines" in r]
    if depths:
        signals.retrieval_depth_avg = sum(depths) / len(depths)
    if lines:
        signals.lines_loaded_avg = sum(lines) / len(lines)

    feedback = [
        r["feedback"] for r in touching
        if r.get("feedback") is not None
    ]
    if feedback:
        total = len(feedback)
        signals.feedback_pass_rate = sum(1 for f in feedback if f.get("quality") == "pass") / total
        signals.feedback_fail_rate = sum(1 for f in feedback if f.get("quality") == "fail") / total


def score_room(signals: RoomSignals) -> tuple[str, list[str]]:
    """Return (status, actions) for a room given its signals."""
    actions: list[str] = []

    # Critical conditions
    if signals.main_lines > 200:
        actions.append("Run /locus-consolidate on this room (main file over 200-line limit)")
    if signals.max_specialty_lines > 300:
        actions.append("Split the oversized specialty file (over 300-line limit)")
    if signals.feedback_fail_rate is not None and signals.feedback_fail_rate > 0.3:
        actions.append("Review room structure — fail rate exceeds 30%")

    if actions:
        return "critical", actions

    # Degraded conditions
    if signals.main_lines > 150:
        actions.append("Run /locus-consolidate on this room (main file approaching 200-line limit)")
    if signals.session_log_count > 5:
        actions.append(f"Run /locus-consolidate on this room ({signals.session_log_count} unprocessed session logs)")
    if signals.oldest_session_days is not None and signals.oldest_session_days > 30:
        actions.append("Archive or consolidate stale session logs (oldest is over 30 days)")
    if signals.retrieval_depth_avg is not None and signals.retrieval_depth_avg > 3.5:
        actions.append("Improve INDEX.md description for this room to reduce retrieval depth")
    if signals.feedback_fail_rate is not None and signals.feedback_fail_rate > 0.15:
        actions.append("Review room structure — fail rate exceeds 15%")

    if actions:
        return "degraded", actions

    # Stale: no sessions, no recent metrics, tiny main file
    no_metrics = signals.retrieval_depth_avg is None
    if signals.session_log_count == 0 and no_metrics and signals.main_lines < 10:
        return "stale", ["Consider archiving or deleting this room (no usage detected)"]

    return "healthy", []


def compute_global_feedback(runs: list[dict]) -> tuple[float | None, float | None]:
    feedback = [r["feedback"] for r in runs if r.get("feedback") is not None]
    if not feedback:
        return None, None
    total = len(feedback)
    pass_rate = sum(1 for f in feedback if f.get("quality") == "pass") / total
    fail_rate = sum(1 for f in feedback if f.get("quality") == "fail") / total
    return pass_rate, fail_rate
