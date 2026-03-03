"""Data model for palace audit results.

Schema defined in spec/health-report-format.md.
Algorithm defined in spec/audit-algorithm.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RoomStatus = str  # "healthy" | "degraded" | "critical" | "stale"


@dataclass
class RoomSignals:
    main_lines: int = 0
    specialty_files: int = 0
    max_specialty_lines: int = 0
    session_log_count: int = 0
    oldest_session_days: float | None = None
    retrieval_depth_avg: float | None = None   # Type A runs only
    lines_loaded_avg: float | None = None
    feedback_pass_rate: float | None = None
    feedback_fail_rate: float | None = None
    has_recent_metrics: bool = False           # any run within 90 days


@dataclass
class RoomResult:
    path: str                          # relative to palace root
    status: RoomStatus
    signals: RoomSignals
    actions: list[str] = field(default_factory=list)


@dataclass
class AuditSummary:
    total_rooms: int = 0
    critical: int = 0
    degraded: int = 0
    stale: int = 0
    healthy: int = 0
    unstructured_dirs: int = 0
    metrics_runs_analysed: int = 0
    global_pass_rate: float | None = None
    global_fail_rate: float | None = None


@dataclass
class AuditResult:
    audited_at: str
    palace_path: str
    index_lines: int
    rooms: list[RoomResult] = field(default_factory=list)
    summary: AuditSummary = field(default_factory=AuditSummary)
    action_items: list[dict[str, Any]] = field(default_factory=list)
    has_metrics: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "audited_at": self.audited_at,
            "palace_path": self.palace_path,
            "index_lines": self.index_lines,
            "rooms": [
                {
                    "path": r.path,
                    "status": r.status,
                    "signals": {
                        "main_lines": r.signals.main_lines,
                        "specialty_files": r.signals.specialty_files,
                        "max_specialty_lines": r.signals.max_specialty_lines,
                        "session_log_count": r.signals.session_log_count,
                        "oldest_session_days": r.signals.oldest_session_days,
                        "retrieval_depth_avg": r.signals.retrieval_depth_avg,
                        "lines_loaded_avg": r.signals.lines_loaded_avg,
                        "feedback_pass_rate": r.signals.feedback_pass_rate,
                        "feedback_fail_rate": r.signals.feedback_fail_rate,
                    },
                    "actions": r.actions,
                }
                for r in self.rooms
            ],
            "summary": {
                "total_rooms": self.summary.total_rooms,
                "critical": self.summary.critical,
                "degraded": self.summary.degraded,
                "stale": self.summary.stale,
                "healthy": self.summary.healthy,
                "unstructured_dirs": self.summary.unstructured_dirs,
                "metrics_runs_analysed": self.summary.metrics_runs_analysed,
                "global_pass_rate": self.summary.global_pass_rate,
                "global_fail_rate": self.summary.global_fail_rate,
            },
            "action_items": self.action_items,
        }
