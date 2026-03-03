"""Metrics collection for Locus runs.

Tracks file reads via a PreToolUse hook — zero impact on agent output.
Schema defined in spec/metrics-schema.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any


def _sdk_version() -> str | None:
    try:
        return pkg_version("claude-agent-sdk")
    except Exception:
        return None


@dataclass
class FileRead:
    path: str
    lines: int | None  # None if line count unavailable (e.g. binary)


@dataclass
class RunMetrics:
    palace_path: str
    task: str
    model: str | None = None
    query_type: str | None = None  # "A" | "B" | "C" | "D" | None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    files_read: list[FileRead] = field(default_factory=list)
    total_cost_usd: float | None = None
    suggestions: list[str] = field(default_factory=list)

    @property
    def retrieval_depth(self) -> int:
        return len(self.files_read)

    @property
    def total_lines(self) -> int:
        return sum(r.lines for r in self.files_read if r.lines is not None)

    @property
    def estimated_tokens(self) -> int:
        return self.total_lines * 15  # ~15 tokens/line heuristic (see spec/size-limits.md)

    def finish(self, cost_usd: float | None = None, model: str | None = None) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.total_cost_usd = cost_usd
        if model:
            self.model = model

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "palace_path": self.palace_path,
            "task": self.task,
            "query_type": self.query_type,
            "agent": {
                "model": self.model,
                "sdk_version": _sdk_version(),
            },
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retrieval_depth": self.retrieval_depth,
            "total_lines": self.total_lines,
            "estimated_tokens": self.estimated_tokens,
            "total_cost_usd": self.total_cost_usd,
            "files_read": [{"path": r.path, "lines": r.lines} for r in self.files_read],
            "feedback": None,
            "suggestions": self.suggestions,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def summary(self) -> str:
        lines = [
            "── Locus Run Metrics ──────────────────────────",
            f"  Palace:          {self.palace_path}",
            f"  Retrieval depth: {self.retrieval_depth} files",
            f"  Total lines:     {self.total_lines}",
            f"  Est. tokens:     {self.estimated_tokens}",
        ]
        if self.total_cost_usd is not None:
            lines.append(f"  Cost:            ${self.total_cost_usd:.4f}")
        lines.append("  Files read:")
        for r in self.files_read:
            line_str = f"{r.lines} lines" if r.lines is not None else "unknown"
            lines.append(f"    {r.path} ({line_str})")
        if self.suggestions:
            lines.append("  Suggestions:")
            for s in self.suggestions:
                lines.append(f"    · {s}")
        lines.append("────────────────────────────────────────────────")
        return "\n".join(lines)

    def default_output_path(self) -> Path:
        """Returns the default _metrics/ path within the palace."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        return Path(self.palace_path) / "_metrics" / f"{ts}.json"


class MetricsCollector:
    """Collects file-read metrics via a PreToolUse hook."""

    def __init__(self, metrics: RunMetrics) -> None:
        self._metrics = metrics

    async def hook(self, input_data: dict, tool_use_id: str, context: Any) -> dict:
        """PreToolUse hook — records Read tool calls, allows all tools to proceed."""
        if input_data.get("tool_name") != "Read":
            return {}

        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        lines = None
        if file_path:
            try:
                p = Path(file_path)
                if p.is_file():
                    lines = sum(1 for _ in p.open("r", errors="replace"))
            except OSError:
                pass

        self._metrics.files_read.append(FileRead(path=file_path, lines=lines))
        return {}  # allow the tool to proceed
