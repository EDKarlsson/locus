"""Locus agent CLI entrypoint.

Usage:
    python -m locus.agent --palace <path> --task <prompt> [options]
    locus --palace <path> --task <prompt> [options]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anyio
from claude_agent_sdk import HookMatcher, query
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from .config import build_options
from .metrics import MetricsCollector, RunMetrics


async def run(
    palace_path: Path,
    task: str,
    max_turns: int = 20,
    output_json: bool = False,
    metrics_file: Path | None = None,
    query_type: str | None = None,
) -> RunMetrics:
    """Run a Locus agent against a palace directory.

    Returns the run metrics. Metrics are written to _metrics/ in the palace
    by default, or to --metrics-file when provided (e.g. for benchmark runs).
    """
    palace_path = palace_path.resolve()
    if not palace_path.is_dir():
        raise ValueError(f"Palace path does not exist or is not a directory: {palace_path}")

    index = palace_path / "INDEX.md"
    if not index.exists():
        print(f"Warning: no INDEX.md found in {palace_path}", file=sys.stderr)

    metrics = RunMetrics(palace_path=str(palace_path), task=task, query_type=query_type)
    collector = MetricsCollector(metrics)

    options = build_options(palace_path, max_turns=max_turns)
    options.hooks = {
        "PreToolUse": [
            HookMatcher(matcher="Read", hooks=[collector.hook]),
        ],
    }

    async for message in query(prompt=task, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and not output_json:
                    print(block.text, flush=True)
        elif isinstance(message, ResultMessage):
            metrics.finish(cost_usd=message.total_cost_usd)

    if not output_json:
        print(f"\n{metrics.summary()}")

    out_path = metrics_file or metrics.default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(metrics.to_json())

    return metrics


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="locus",
        description="Run a Locus memory agent against a palace directory.",
    )
    parser.add_argument(
        "--palace",
        required=True,
        type=Path,
        help="Path to the palace root directory (must contain INDEX.md).",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="The task or query to run against the palace.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
        help="Maximum agent turns (default: 20).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output metrics as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=None,
        help="Write metrics JSON to this path instead of palace/_metrics/.",
    )
    parser.add_argument(
        "--query-type",
        choices=["A", "B", "C", "D"],
        default=None,
        help="Benchmark query type (A=specific fact, B=cross-domain, C=recency, D=troubleshooting).",
    )

    args = parser.parse_args()

    metrics = anyio.run(
        run,
        args.palace,
        args.task,
        args.max_turns,
        args.output_json,
        args.metrics_file,
        args.query_type,
    )

    if args.output_json:
        print(metrics.to_json())


if __name__ == "__main__":
    cli()
