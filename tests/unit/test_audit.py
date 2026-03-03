"""Unit tests for locus.audit — scanner, model, and report (#18).

Tests cover:
- Room discovery
- Per-room signal collection
- Scoring logic (all four statuses)
- Metrics enrichment
- Global feedback computation
- Report rendering (markdown structure)
- AuditResult.to_dict() schema shape
- CLI run_audit() integration
"""

import json
import textwrap
from pathlib import Path

import pytest

from locus.audit.model import AuditResult, AuditSummary, RoomResult, RoomSignals
from locus.audit.scanner import (
    collect_room_signals,
    compute_global_feedback,
    discover_rooms,
    enrich_with_metrics,
    load_metrics,
    score_room,
)
from locus.audit.report import render_markdown, write_reports
from locus.audit.main import run_audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_palace(tmp_path: Path, rooms: dict) -> Path:
    """Build a minimal palace from a dict of {room_rel_path: main_line_count}.

    Also writes INDEX.md and optionally specialty files / session logs
    if the value is a dict with keys 'lines', 'specialty', 'sessions'.
    """
    (tmp_path / "INDEX.md").write_text("# Index\n" * 10)

    for rel, spec in rooms.items():
        if isinstance(spec, int):
            spec = {"lines": spec}
        room_dir = tmp_path / rel
        room_dir.mkdir(parents=True, exist_ok=True)
        name = room_dir.name
        (room_dir / f"{name}.md").write_text("line\n" * spec.get("lines", 10))

        for i, sl in enumerate(spec.get("sessions", [])):
            sessions = room_dir / "sessions"
            sessions.mkdir(exist_ok=True)
            (sessions / f"2026-03-0{i+1}.md").write_text("line\n" * sl)

        for i, sl in enumerate(spec.get("specialty", [])):
            (room_dir / f"specialty-{i}.md").write_text("line\n" * sl)

    return tmp_path


def make_metrics_file(tmp_path: Path, runs: list[dict]) -> None:
    metrics_dir = tmp_path / "_metrics"
    metrics_dir.mkdir(exist_ok=True)
    for i, run in enumerate(runs):
        (metrics_dir / f"2026-03-02T{i:06d}Z.json").write_text(json.dumps(run))


# ---------------------------------------------------------------------------
# Room discovery
# ---------------------------------------------------------------------------

class TestRoomDiscovery:
    def test_discovers_matching_rooms(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 10, "global/tools": 5})
        rooms, unstructured = discover_rooms(tmp_path)
        paths = {r.name for r in rooms}
        assert "api" in paths
        assert "tools" in paths

    def test_unstructured_dirs_counted(self, tmp_path):
        make_palace(tmp_path, {})
        orphan = tmp_path / "orphan"
        orphan.mkdir()
        (orphan / "somefile.md").write_text("x")
        _, unstructured = discover_rooms(tmp_path)
        assert unstructured == 1

    def test_metrics_dir_excluded(self, tmp_path):
        make_palace(tmp_path, {})
        (tmp_path / "_metrics").mkdir()
        (tmp_path / "_metrics" / "_metrics.md").write_text("x")
        rooms, _ = discover_rooms(tmp_path)
        assert all("_metrics" not in str(r) for r in rooms)

    def test_sessions_dir_not_treated_as_room(self, tmp_path):
        make_palace(tmp_path, {"projects/api": {"lines": 10, "sessions": [5]}})
        rooms, _ = discover_rooms(tmp_path)
        assert all(r.name != "sessions" for r in rooms)


# ---------------------------------------------------------------------------
# Signal collection
# ---------------------------------------------------------------------------

class TestSignalCollection:
    def test_main_lines_counted(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 42})
        room_dir = tmp_path / "projects" / "api"
        sig = collect_room_signals(room_dir)
        assert sig.main_lines == 42

    def test_session_log_count(self, tmp_path):
        make_palace(tmp_path, {"projects/api": {"lines": 10, "sessions": [5, 5, 5]}})
        room_dir = tmp_path / "projects" / "api"
        sig = collect_room_signals(room_dir)
        assert sig.session_log_count == 3

    def test_specialty_files_counted(self, tmp_path):
        make_palace(tmp_path, {"projects/api": {"lines": 10, "specialty": [20, 30]}})
        room_dir = tmp_path / "projects" / "api"
        sig = collect_room_signals(room_dir)
        assert sig.specialty_files == 2
        assert sig.max_specialty_lines == 30

    def test_no_sessions_dir(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 10})
        sig = collect_room_signals(tmp_path / "projects" / "api")
        assert sig.session_log_count == 0
        assert sig.oldest_session_days is None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:
    def test_healthy(self):
        sig = RoomSignals(main_lines=50, session_log_count=2)
        status, actions = score_room(sig)
        assert status == "healthy"
        assert actions == []

    def test_critical_main_lines(self):
        sig = RoomSignals(main_lines=201)
        status, actions = score_room(sig)
        assert status == "critical"
        assert any("200-line limit" in a for a in actions)

    def test_critical_specialty_lines(self):
        sig = RoomSignals(main_lines=50, max_specialty_lines=301)
        status, actions = score_room(sig)
        assert status == "critical"

    def test_critical_fail_rate(self):
        sig = RoomSignals(main_lines=50, feedback_fail_rate=0.35)
        status, actions = score_room(sig)
        assert status == "critical"
        assert any("30%" in a for a in actions)

    def test_degraded_session_logs(self):
        sig = RoomSignals(main_lines=50, session_log_count=6)
        status, actions = score_room(sig)
        assert status == "degraded"
        assert any("6 unprocessed" in a for a in actions)

    def test_degraded_main_lines(self):
        sig = RoomSignals(main_lines=160)
        status, actions = score_room(sig)
        assert status == "degraded"

    def test_degraded_retrieval_depth(self):
        sig = RoomSignals(main_lines=50, retrieval_depth_avg=4.0)
        status, actions = score_room(sig)
        assert status == "degraded"
        assert any("INDEX.md" in a for a in actions)

    def test_stale(self):
        sig = RoomSignals(main_lines=5, session_log_count=0, retrieval_depth_avg=None)
        status, actions = score_room(sig)
        assert status == "stale"

    def test_not_stale_if_has_metrics(self):
        sig = RoomSignals(main_lines=5, session_log_count=0, retrieval_depth_avg=2.0)
        status, _ = score_room(sig)
        assert status == "healthy"

    def test_critical_takes_priority_over_degraded(self):
        # Both critical and degraded conditions present
        sig = RoomSignals(main_lines=210, session_log_count=7)
        status, _ = score_room(sig)
        assert status == "critical"


# ---------------------------------------------------------------------------
# Metrics enrichment
# ---------------------------------------------------------------------------

class TestMetricsEnrichment:
    def test_enriches_retrieval_depth(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 10})
        runs = [
            {"files_read": [{"path": "projects/api/api.md", "lines": 10}],
             "retrieval_depth": 2, "total_lines": 30, "feedback": None},
            {"files_read": [{"path": "projects/api/api.md", "lines": 10}],
             "retrieval_depth": 4, "total_lines": 50, "feedback": None},
        ]
        sig = RoomSignals()
        enrich_with_metrics(tmp_path / "projects" / "api", tmp_path, sig, runs)
        assert sig.retrieval_depth_avg == pytest.approx(3.0)

    def test_enriches_feedback_rates(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 10})
        runs = [
            {"files_read": [{"path": "projects/api/api.md", "lines": 10}],
             "retrieval_depth": 2, "total_lines": 20,
             "feedback": {"quality": "pass"}},
            {"files_read": [{"path": "projects/api/api.md", "lines": 10}],
             "retrieval_depth": 2, "total_lines": 20,
             "feedback": {"quality": "fail"}},
        ]
        sig = RoomSignals()
        enrich_with_metrics(tmp_path / "projects" / "api", tmp_path, sig, runs)
        assert sig.feedback_pass_rate == pytest.approx(0.5)
        assert sig.feedback_fail_rate == pytest.approx(0.5)

    def test_no_touching_runs_leaves_none(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 10})
        runs = [{"files_read": [{"path": "projects/other/other.md", "lines": 5}],
                 "retrieval_depth": 1, "total_lines": 5, "feedback": None}]
        sig = RoomSignals()
        enrich_with_metrics(tmp_path / "projects" / "api", tmp_path, sig, runs)
        assert sig.retrieval_depth_avg is None


# ---------------------------------------------------------------------------
# Global feedback
# ---------------------------------------------------------------------------

class TestGlobalFeedback:
    def test_no_feedback_returns_none(self):
        runs = [{"feedback": None}, {"feedback": None}]
        pr, fr = compute_global_feedback(runs)
        assert pr is None and fr is None

    def test_computes_rates(self):
        runs = [
            {"feedback": {"quality": "pass"}},
            {"feedback": {"quality": "pass"}},
            {"feedback": {"quality": "fail"}},
            {"feedback": None},
        ]
        pr, fr = compute_global_feedback(runs)
        assert pr == pytest.approx(2 / 3)
        assert fr == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# Load metrics
# ---------------------------------------------------------------------------

class TestLoadMetrics:
    def test_loads_json_files(self, tmp_path):
        make_metrics_file(tmp_path, [{"retrieval_depth": 2}, {"retrieval_depth": 3}])
        runs = load_metrics(tmp_path)
        assert len(runs) == 2

    def test_skips_audit_files(self, tmp_path):
        metrics_dir = tmp_path / "_metrics"
        metrics_dir.mkdir()
        (metrics_dir / "audit-2026.json").write_text('{"schema_version": "1"}')
        (metrics_dir / "2026-03-02T000000Z.json").write_text('{"retrieval_depth": 1}')
        runs = load_metrics(tmp_path)
        assert len(runs) == 1

    def test_empty_if_no_metrics_dir(self, tmp_path):
        assert load_metrics(tmp_path) == []


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

class TestReportRendering:
    def _make_result(self, rooms=None) -> AuditResult:
        return AuditResult(
            audited_at="2026-03-02T14:30:12Z",
            palace_path="/tmp/palace",
            index_lines=21,
            rooms=rooms or [],
            summary=AuditSummary(total_rooms=0),
            has_metrics=True,
        )

    def test_contains_header(self):
        md = render_markdown(self._make_result())
        assert "# Palace Health Report" in md

    def test_contains_summary_table(self):
        md = render_markdown(self._make_result())
        assert "## Summary" in md
        assert "INDEX.md lines" in md

    def test_no_metrics_note(self):
        result = self._make_result()
        result.has_metrics = False
        md = render_markdown(result)
        assert "_metrics/" in md
        assert "no" in md.lower()

    def test_action_items_section(self):
        result = self._make_result()
        result.action_items = [
            {"priority": 1, "status": "critical", "room": "projects/api", "action": "Consolidate"}
        ]
        md = render_markdown(result)
        assert "## Action Items" in md
        assert "Consolidate" in md

    def test_room_section_per_room(self):
        rooms = [
            RoomResult("projects/api", "healthy", RoomSignals(main_lines=50)),
            RoomResult("global/tools", "degraded", RoomSignals(main_lines=160)),
        ]
        md = render_markdown(self._make_result(rooms))
        assert "projects/api" in md
        assert "global/tools" in md

    def test_critical_icon_in_room(self):
        rooms = [RoomResult("projects/api", "critical", RoomSignals(main_lines=210))]
        md = render_markdown(self._make_result(rooms))
        assert "🔴" in md


# ---------------------------------------------------------------------------
# AuditResult.to_dict() schema
# ---------------------------------------------------------------------------

class TestAuditSchema:
    def test_schema_version(self):
        result = AuditResult("2026-03-02T00:00:00Z", "/tmp", 21)
        d = result.to_dict()
        assert d["schema_version"] == "1"

    def test_required_top_level_keys(self):
        d = AuditResult("2026-03-02T00:00:00Z", "/tmp", 21).to_dict()
        assert {"schema_version", "audited_at", "palace_path", "index_lines",
                "rooms", "summary", "action_items"} <= d.keys()

    def test_summary_keys(self):
        d = AuditResult("2026-03-02T00:00:00Z", "/tmp", 21).to_dict()
        assert {"total_rooms", "critical", "degraded", "stale", "healthy",
                "unstructured_dirs", "metrics_runs_analysed"} <= d["summary"].keys()


# ---------------------------------------------------------------------------
# write_reports
# ---------------------------------------------------------------------------

class TestWriteReports:
    def test_writes_md_and_json(self, tmp_path):
        result = AuditResult("2026-03-02T14:30:12+00:00", str(tmp_path), 21)
        md_path, json_path = write_reports(result, tmp_path)
        assert md_path.exists()
        assert json_path.exists()

    def test_writes_last_audit(self, tmp_path):
        result = AuditResult("2026-03-02T14:30:12+00:00", str(tmp_path), 21)
        write_reports(result, tmp_path)
        last = tmp_path / "_metrics" / "_last-audit.txt"
        assert last.exists()
        assert "2026" in last.read_text()

    def test_json_is_valid(self, tmp_path):
        result = AuditResult("2026-03-02T14:30:12+00:00", str(tmp_path), 21)
        _, json_path = write_reports(result, tmp_path)
        data = json.loads(json_path.read_text())
        assert data["schema_version"] == "1"


# ---------------------------------------------------------------------------
# run_audit() integration
# ---------------------------------------------------------------------------

class TestRunAudit:
    def test_healthy_palace(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 50, "global/tools": 30})
        result = run_audit(tmp_path)
        assert result.summary.total_rooms == 2
        assert result.summary.critical == 0
        assert result.summary.healthy == 2

    def test_critical_room_detected(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 210})
        result = run_audit(tmp_path)
        assert result.summary.critical == 1
        assert len(result.action_items) >= 1

    def test_room_filter(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 50, "projects/data": 210})
        result = run_audit(tmp_path, room_filter="data")
        assert result.summary.total_rooms == 1
        assert result.rooms[0].path == "projects/data"

    def test_no_metrics_graceful(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 50})
        result = run_audit(tmp_path)
        assert result.has_metrics is False
        assert result.summary.metrics_runs_analysed == 0

    def test_with_metrics(self, tmp_path):
        make_palace(tmp_path, {"projects/api": 50})
        make_metrics_file(tmp_path, [
            {"files_read": [{"path": "projects/api/api.md", "lines": 50}],
             "retrieval_depth": 2, "total_lines": 70, "feedback": None}
        ])
        result = run_audit(tmp_path)
        assert result.has_metrics is True
        assert result.summary.metrics_runs_analysed == 1

    def test_unstructured_dir_emits_action_item(self, tmp_path):
        """Directories with .md files but no <dirname>.md should produce an action item."""
        make_palace(tmp_path, {"projects/api": 50})
        # Create an orphan directory: has .md files but no api-orphan.md main file
        orphan = tmp_path / "projects" / "api-orphan"
        orphan.mkdir(parents=True)
        (orphan / "some-notes.md").write_text("notes\n")
        result = run_audit(tmp_path)
        assert result.summary.unstructured_dirs == 1
        unstructured_actions = [
            item for item in result.action_items
            if item.get("room") == "(unstructured)"
        ]
        assert len(unstructured_actions) == 1
        assert "main file" in unstructured_actions[0]["action"]
