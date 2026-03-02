"""Metrics collection for Locus benchmark runs.

Tracks file reads via a PreToolUse hook — zero impact on agent output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FileRead:
    path: str
    lines: int | None  # None if line count unavailable (e.g. binary)


@dataclass
class RunMetrics:
    palace_path: str
    task: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    files_read: list[FileRead] = field(default_factory=list)
    total_cost_usd: float | None = None

    @property
    def retrieval_depth(self) -> int:
        return len(self.files_read)

    @property
    def total_lines(self) -> int:
        return sum(r.lines for r in self.files_read if r.lines is not None)

    @property
    def estimated_tokens(self) -> int:
        return self.total_lines * 15  # ~15 tokens/line heuristic (see spec/size-limits.md)

    def finish(self, cost_usd: float | None = None) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.total_cost_usd = cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "palace_path": self.palace_path,
            "task": self.task,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retrieval_depth": self.retrieval_depth,
            "total_lines": self.total_lines,
            "estimated_tokens": self.estimated_tokens,
            "total_cost_usd": self.total_cost_usd,
            "files_read": [{"path": r.path, "lines": r.lines} for r in self.files_read],
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
        lines.append("────────────────────────────────────────────────")
        return "\n".join(lines)


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
