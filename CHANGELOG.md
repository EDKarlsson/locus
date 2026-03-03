# Changelog

## v0.6.0 — 2026-03-02

### Public Release — History squash, bug fixes, registry assets

**History**
- 31 commits squashed to 6 clean milestone commits (`feat(v0.1)` through `feat(v0.6)`)
- Personal local paths and private project references removed from `CLAUDE.md`,
  `SPECIFICATION.md`, and `spec/reference-analysis.md`

**Audit fixes**
- `fix(audit)`: stale-room check now requires no `_metrics/` activity in the last
  **90 days** (not just "no metrics ever") — `RoomSignals.has_recent_metrics` tracks
  this via `_is_recent()` on each run's `started_at` timestamp
- `fix(audit)`: `retrieval_depth_avg` is now computed from **Type A runs only**
  (`query_type == "A"`) per `spec/audit-algorithm.md`; non-benchmark runs no longer
  inflate the degraded signal
- +4 tests → 181 total

**MCP security**
- `fix(mcp)`: SEC-002 — `_MAX_READ_BYTES` (500 KB) bounds `memory_read` and
  `memory_list` file reads; `_MAX_WRITE_BYTES` (500 KB) rejects oversized writes
  before any file I/O; `_read_bounded()` centralises both read paths
- +2 tests → 183 total

**Registry**
- `smithery.yaml` — Smithery.ai stdio config: `uvx locus-mcp` with `palace` path
  as optional configSchema field
- `server.json` — Official MCP Registry format (`io.github.EDKarlsson/locus`,
  PyPI package `locus-mcp` v0.6.0); also used by Glama.ai
- For mcp.so: `npx mcp-index https://github.com/EDKarlsson/locus`

---

### MCP Integration Benchmarks + Architecture Docs

Adds two live MCP benchmark scripts, a palace-vs-flat recall comparison harness,
architecture diagrams, and benchmark charts for the repo.

**New scripts (`scripts/`)**

- `bench-mcp.py` — 40-case integration benchmark covering all 4 MCP tools across
  navigation, safety, search, write, fidelity, and edge categories. Runs against
  a live `locus-mcp` subprocess. Key fix: FastMCP surfaces `ValueError` as
  `isError=True` tool results (not Python exceptions) — use `resp.isError`, not
  `try/except`, to detect guard rejections.
- `bench-compare.py` — 9-scenario recall benchmark comparing palace vs flat-palace.
  Measures lines loaded into context and answer recall per query. Results: palace
  loads 52% fewer lines on average; flat misses session-only queries entirely.
- `generate-charts.py` — Regenerates `docs/img/` SVG charts from benchmark data.
  Requires `matplotlib` (added to `[dev]` optional dependency group).

**New fixture (`tests/fixtures/flat-palace/`)**

Flat baseline palace: `INDEX.md` + `MEMORY.md` (184 lines, all content in one file).
Used as the comparison target for `bench-compare.py`.

**New docs (`docs/`)**

- `architecture.md` — Four Mermaid diagrams: palace structure with line counts,
  MCP server internals (main/server/palace modules), agent interfaces
  (Claude/SDK/Codex/Gemini), memory lifecycle (query → consolidate loop).
- `benchmarks.md` — Benchmark methodology, results summary, and embedded charts.
- `img/lines-comparison.svg` — Grouped bar chart: palace vs flat lines loaded per scenario.
- `img/latency-by-category.svg` — Horizontal bar chart: MCP avg latency by tool category.

**README** updated: Benchmarking section now references the two new scripts and
their summary results; Structure section reflects new scripts and docs layout.

---

## v0.5.0 — 2026-03-02

### MCP Server

Adds `locus-mcp` — a stdio MCP server exposing the memory palace to any
MCP-capable client (Claude Desktop, Cursor, Zed) without requiring skill files.

**New package: `locus/mcp/`**

- `palace.py` — palace root resolution (`--palace`, `LOCUS_PALACE`, `.locus/`, `~/.locus/`);
  path-traversal guard; write-blocked dir check at any depth; extension allowlist
- `server.py` — `FastMCP` instance with four tools:
  - `memory_list(path?)` — returns `INDEX.md` or lists a room directory
  - `memory_read(path)` — reads any file in the palace
  - `memory_write(path, content)` — atomic write (temp-rename); blocks writes to
    `_metrics/`, `sessions/`, `archived/` at any nesting depth
  - `memory_search(query, path?)` — full-text search via `rg --json`; Python `re` fallback
- `main.py` — `locus-mcp` CLI entry point

**Supporting files**

- `spec/mcp-server.md` — architecture, tool surface, safety model, client config examples
- `scripts/try-mcp.py` — stdio client smoke test (exercises all four tools)
- `tests/unit/test_mcp.py` — 41 tests covering palace utilities and all MCP tools
- `.mcp.json` (gitignored) — local dev config pointing at `tests/fixtures/palace`

**Notable fix**: `rg` text output format breaks on filenames containing `-`
(e.g., `technical-gotchas.md`). Switched to `rg --json` for unambiguous path parsing.

---

## v0.4.0 — 2026-03-02

### Self Evaluation

**#16 — Audit algorithm spec** (`spec/audit-algorithm.md`)
Room discovery by `<dir>/<dir>.md` pattern; four health statuses
(critical / degraded / stale / healthy); scoring thresholds for file size,
session count, retrieval depth, and feedback rates.

**#17 — Health report format** (`spec/health-report-format.md`)
Markdown + JSON sidecar at `_metrics/audit-YYYY-MM-DDTHHMMSSZ.{md,json}`;
`_metrics/_last-audit.txt` timestamp file.

**#18 — `locus-audit` implementation** (`locus/audit/`, `skills/claude/locus-audit/`)
Full Python package: `model.py`, `scanner.py`, `report.py`, `main.py`.
`locus-audit` CLI entry point. 43 unit tests.

**#19 — Inferred disagreement signal** (`locus/feedback/signals.py`)
`classify_message()` detects implicit fail/partial signals in user follow-ups.
Fail patterns always win over partial patterns at all confidence tiers.
Step 7 added to `skills/claude/locus/SKILL.md`. 58 unit tests.

---

## v0.3 — 2026-03-02

### Performance Metrics

**#13 — Metrics schema** (`spec/metrics-schema.md`, `locus/agent/metrics.py`)
Schema v1: `schema_version`, `query_type`, `agent{model, sdk_version}`,
`feedback`, `suggestions[]`. Default storage at `palace/_metrics/`.

**#14 — `locus-feedback` skill**
`/locus-feedback <pass|partial|fail> [note]` — records quality feedback on
the most recent `_metrics/*.json` file.

**#15 — Suggestion logic + tests**
`generate_suggestions()` in `RunMetrics`; thresholds by query type (A/B/C/D).
First pytest infrastructure: `tests/unit/test_metrics.py` (33 tests).

---

## v0.2.0 — 2026-03-02

### Core Palace

- Templates: `INDEX.md`, room main file, session log
- Skills: Claude Code (`skills/claude/`), Codex (`skills/codex/`), Gemini (`skills/gemini/`)
- Python Agent SDK: `locus.agent` package, `locus` CLI, metrics collector
- Benchmark: 15-query palace vs flat fixture; palace 87% pass / 0% fail,
  flat 73% pass / 13% fail

---

## v0.1.0 — 2026-03-02

### Foundation

- Conventions: INDEX format, room conventions, size limits, write modes
- Spec: `spec/index-format.md`, `spec/room-conventions.md`, `spec/size-limits.md`,
  `spec/write-modes.md`
- Benchmark fixtures: `tests/fixtures/palace/` and `tests/fixtures/flat/`
- README and SPECIFICATION.md
