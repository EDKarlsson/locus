"""Unit tests for locus.agent.metrics.

Covers schema shape (#13), suggestion logic (#15), and the structures
consumed by the feedback skill (#14).
"""

import json
import tempfile
from pathlib import Path

import pytest

from locus.agent.metrics import FileRead, MetricsCollector, RunMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_metrics(
    *,
    files: list[tuple[str, int]] | None = None,
    query_type: str | None = None,
    palace: str = "/tmp/palace",
    task: str = "test query",
) -> RunMetrics:
    m = RunMetrics(palace_path=palace, task=task, query_type=query_type)
    for path, lines in (files or []):
        m.files_read.append(FileRead(path=path, lines=lines))
    return m


# ---------------------------------------------------------------------------
# Schema shape (#13)
# ---------------------------------------------------------------------------

class TestSchemaShape:
    def test_schema_version_is_string_one(self):
        d = make_metrics().to_dict()
        assert d["schema_version"] == "1"

    def test_required_fields_present(self):
        d = make_metrics().to_dict()
        required = {
            "schema_version", "palace_path", "task", "query_type",
            "agent", "started_at", "finished_at",
            "retrieval_depth", "total_lines", "estimated_tokens",
            "total_cost_usd", "files_read", "feedback", "suggestions",
        }
        assert required <= d.keys()

    def test_agent_subfields(self):
        d = make_metrics().to_dict()
        assert "model" in d["agent"]
        assert "sdk_version" in d["agent"]

    def test_feedback_is_null_by_default(self):
        d = make_metrics().to_dict()
        assert d["feedback"] is None

    def test_suggestions_is_empty_list_by_default(self):
        d = make_metrics().to_dict()
        assert d["suggestions"] == []

    def test_query_type_null_by_default(self):
        d = make_metrics().to_dict()
        assert d["query_type"] is None

    def test_query_type_propagated(self):
        d = make_metrics(query_type="A").to_dict()
        assert d["query_type"] == "A"

    def test_to_json_is_valid_json(self):
        j = make_metrics().to_json()
        parsed = json.loads(j)
        assert parsed["schema_version"] == "1"

    def test_files_read_structure(self):
        m = make_metrics(files=[("INDEX.md", 21), ("room.md", 55)])
        d = m.to_dict()
        assert d["files_read"] == [
            {"path": "INDEX.md", "lines": 21},
            {"path": "room.md", "lines": 55},
        ]

    def test_files_read_none_lines(self):
        m = RunMetrics(palace_path="/tmp", task="t")
        m.files_read.append(FileRead(path="binary.bin", lines=None))
        d = m.to_dict()
        assert d["files_read"][0]["lines"] is None


# ---------------------------------------------------------------------------
# Computed properties
# ---------------------------------------------------------------------------

class TestComputedProperties:
    def test_retrieval_depth(self):
        m = make_metrics(files=[("a.md", 10), ("b.md", 20)])
        assert m.retrieval_depth == 2

    def test_total_lines_skips_none(self):
        m = RunMetrics(palace_path="/tmp", task="t")
        m.files_read = [
            FileRead("a.md", 10),
            FileRead("b.bin", None),
            FileRead("c.md", 30),
        ]
        assert m.total_lines == 40

    def test_estimated_tokens(self):
        m = make_metrics(files=[("a.md", 100)])
        assert m.estimated_tokens == 1500  # 100 * 15

    def test_finish_sets_timestamps_and_cost(self):
        m = make_metrics()
        assert m.finished_at is None
        m.finish(cost_usd=0.0042, model="claude-sonnet-4-6")
        assert m.finished_at is not None
        assert m.total_cost_usd == pytest.approx(0.0042)
        assert m.model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Default output path
# ---------------------------------------------------------------------------

class TestDefaultOutputPath:
    def test_path_is_under_metrics_dir(self):
        m = make_metrics(palace="/tmp/mypalace")
        p = m.default_output_path()
        assert p.parent == Path("/tmp/mypalace/_metrics")

    def test_path_has_json_extension(self):
        m = make_metrics()
        assert m.default_output_path().suffix == ".json"

    def test_path_filename_no_colons(self):
        # Safe for all filesystems
        m = make_metrics()
        assert ":" not in m.default_output_path().name


# ---------------------------------------------------------------------------
# Suggestion logic (#15)
# ---------------------------------------------------------------------------

class TestSuggestions:
    def test_no_suggestions_healthy_type_a(self):
        # depth=3, lines=134 — within thresholds
        m = make_metrics(
            query_type="A",
            files=[("INDEX.md", 21), ("room.md", 55), ("services.md", 58)],
        )
        assert m.generate_suggestions() == []

    def test_type_a_depth_exceeds_threshold(self):
        # depth=4 > 3
        m = make_metrics(
            query_type="A",
            files=[("INDEX.md", 21), ("room.md", 55), ("a.md", 20), ("b.md", 20)],
        )
        suggestions = m.generate_suggestions()
        assert len(suggestions) == 1
        assert "INDEX.md" in suggestions[0]
        assert "4 files" in suggestions[0]

    def test_type_a_lines_exceed_flat_baseline(self):
        # lines=200 > 184
        m = make_metrics(
            query_type="A",
            files=[("INDEX.md", 21), ("room.md", 55), ("a.md", 124)],
        )
        suggestions = m.generate_suggestions()
        assert any("200 lines" in s for s in suggestions)
        assert any("184" in s for s in suggestions)

    def test_type_a_both_thresholds_breached(self):
        # depth=4 and lines=250
        files = [("INDEX.md", 21), ("room.md", 80), ("a.md", 80), ("b.md", 69)]
        m = make_metrics(query_type="A", files=files)
        assert len(m.generate_suggestions()) == 2

    def test_type_b_healthy(self):
        # depth=4, within threshold of 5
        m = make_metrics(
            query_type="B",
            files=[("INDEX.md", 21), ("room.md", 55), ("gotchas.md", 67), ("services.md", 58)],
        )
        assert m.generate_suggestions() == []

    def test_type_b_depth_exceeds_threshold(self):
        # depth=6 > 5
        files = [(f"file{i}.md", 20) for i in range(6)]
        m = make_metrics(query_type="B", files=files)
        suggestions = m.generate_suggestions()
        assert len(suggestions) == 1
        assert "6 files" in suggestions[0]

    def test_type_c_and_d_use_same_threshold_as_b(self):
        files = [(f"f{i}.md", 10) for i in range(6)]
        for qt in ("C", "D"):
            m = make_metrics(query_type=qt, files=files)
            assert len(m.generate_suggestions()) == 1

    def test_no_query_type_generic_threshold(self):
        # depth=5 > 4 generic threshold
        files = [(f"f{i}.md", 10) for i in range(5)]
        m = make_metrics(query_type=None, files=files)
        suggestions = m.generate_suggestions()
        assert len(suggestions) == 1
        assert "specific fact" in suggestions[0]

    def test_no_query_type_within_generic_threshold(self):
        # depth=4 — exactly at threshold, no suggestion
        files = [(f"f{i}.md", 10) for i in range(4)]
        m = make_metrics(query_type=None, files=files)
        assert m.generate_suggestions() == []

    def test_finish_populates_suggestions(self):
        # generate_suggestions called automatically on finish()
        files = [("INDEX.md", 21), ("r.md", 55), ("a.md", 20), ("b.md", 20)]
        m = make_metrics(query_type="A", files=files)
        assert m.suggestions == []
        m.finish()
        assert len(m.suggestions) == 1

    def test_suggestions_in_to_dict(self):
        files = [("INDEX.md", 21), ("r.md", 55), ("a.md", 20), ("b.md", 20)]
        m = make_metrics(query_type="A", files=files)
        m.finish()
        d = m.to_dict()
        assert len(d["suggestions"]) == 1

    def test_suggestions_in_summary(self):
        files = [("INDEX.md", 21), ("r.md", 55), ("a.md", 20), ("b.md", 20)]
        m = make_metrics(query_type="A", files=files)
        m.finish()
        summary = m.summary()
        assert "Suggestions" in summary


# ---------------------------------------------------------------------------
# MetricsCollector hook (#13)
# ---------------------------------------------------------------------------

class TestMetricsCollector:
    @pytest.mark.asyncio
    async def test_hook_records_read_tool(self, tmp_path):
        f = tmp_path / "room.md"
        f.write_text("line1\nline2\nline3\n")

        m = RunMetrics(palace_path=str(tmp_path), task="t")
        collector = MetricsCollector(m)

        await collector.hook(
            {"tool_name": "Read", "tool_input": {"file_path": str(f)}},
            tool_use_id="x",
            context=None,
        )

        assert len(m.files_read) == 1
        assert m.files_read[0].path == str(f)
        assert m.files_read[0].lines == 3

    @pytest.mark.asyncio
    async def test_hook_ignores_non_read_tools(self):
        m = RunMetrics(palace_path="/tmp", task="t")
        collector = MetricsCollector(m)

        await collector.hook(
            {"tool_name": "Bash", "tool_input": {}},
            tool_use_id="x",
            context=None,
        )

        assert len(m.files_read) == 0

    @pytest.mark.asyncio
    async def test_hook_handles_missing_file(self):
        m = RunMetrics(palace_path="/tmp", task="t")
        collector = MetricsCollector(m)

        await collector.hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/nonexistent/path.md"}},
            tool_use_id="x",
            context=None,
        )

        assert len(m.files_read) == 1
        assert m.files_read[0].lines is None

    @pytest.mark.asyncio
    async def test_hook_returns_empty_dict(self, tmp_path):
        m = RunMetrics(palace_path=str(tmp_path), task="t")
        collector = MetricsCollector(m)
        result = await collector.hook(
            {"tool_name": "Read", "tool_input": {"file_path": str(tmp_path)}},
            tool_use_id="x",
            context=None,
        )
        assert result == {}
