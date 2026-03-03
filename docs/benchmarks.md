# Locus Benchmarks

Two benchmark scripts measure Locus against a flat MEMORY.md baseline using
live MCP tool calls against the fixture palaces in `tests/fixtures/`.

---

## Context Load: Palace vs Flat

Each scenario represents an agent answering a specific question via the optimal
navigation path. Palace navigates to one targeted file; flat bulk-loads the full
184-line MEMORY.md every time.

![Lines loaded per scenario](img/lines-comparison.svg)

**Key results** (`bench-compare.py`, 9 scenarios):

| Metric | Palace | Flat |
|---|---|---|
| Total lines loaded | 822 | 1719 |
| Avg lines per query | 91 | 191 |
| Answers found | 9 / 9 | 8 / 9 |
| Avg tool calls | 3.2 | 2.0 |

Palace loads **52% fewer lines** on average. The trade-off is +1.2 tool calls
per query for navigation overhead.

**Where palace wins:** specific queries (50–57% reduction) and session-only
queries (`session-n8n` — not yet consolidated into flat, missed entirely).

**Where flat is competitive:** broad queries needing multiple specialty files
(`broad-infra`) — palace still saves 20% but uses 4 calls vs flat's 2.

> Reproduce: `uv run scripts/bench-compare.py`

---

## MCP Tool Latency

Round-trip latency for each MCP tool category across 40 test cases.

![MCP latency by category](img/latency-by-category.svg)

**Key results** (`bench-mcp.py`, 40 cases, 100% pass):

| Stat | Value |
|---|---|
| Overall avg | 6.8 ms |
| p95 | 15.8 ms |
| Max | 16.5 ms |
| Fastest category | safety (2.0 ms — errors short-circuit before I/O) |
| Slowest category | search (13.7 ms — ripgrep subprocess) |

Safety guard rejections are 7× faster than search because `assert_writable()`
raises before any filesystem access. Search always spawns a `rg` subprocess
regardless of result size.

> Reproduce: `uv run scripts/bench-mcp.py`

---

## Reproducing

```sh
# Install dev dependencies (includes matplotlib)
uv sync --extra dev

# Run the 40-case MCP integration benchmark
uv run scripts/bench-mcp.py

# Run the palace vs flat recall comparison
uv run scripts/bench-compare.py

# Regenerate charts
uv run scripts/generate-charts.py
```

Fixture palaces are in `tests/fixtures/palace/` (hierarchical) and
`tests/fixtures/flat-palace/` (single-file baseline).
