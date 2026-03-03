# Changelog

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
