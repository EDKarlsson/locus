# Locus

Hierarchical markdown-based memory system for autonomous AI agents. Each directory
is a room (locus) in the palace, containing specific knowledge navigated on demand.
Named for the atomic unit of the [Method of Loci](https://en.wikipedia.org/wiki/Method_of_loci).

**Core idea:** Keep context windows small. Load only the room you need, not the whole palace.

---

## How it works

```
palace/
  INDEX.md                    ← always read first (~50 lines max)
  global/
    toolchain/
      toolchain.md            ← canonical facts about tools
  projects/
    my-project/
      my-project.md           ← room overview + key files
      technical-gotchas.md    ← specialty: issues & resolutions
      sessions/
        2026-03-02.md         ← append-only session log
```

An agent reads `INDEX.md`, navigates to the relevant room, and reads only that room.
Session logs accumulate until consolidation merges them into canonical files.

## Installation

**Claude:**
```sh
cp -r skills/claude/locus ~/.claude/skills/locus
cp -r skills/claude/locus-consolidate ~/.claude/skills/locus-consolidate
```

**Codex:**
```sh
cp -r skills/codex/locus ~/.codex/skills/locus
cp -r skills/codex/locus-consolidate ~/.codex/skills/locus-consolidate
```

**Gemini:** Reference `skills/gemini/locus/SKILL.md` from your `.gemini/` directory
or a GitHub Actions workflow.

**Agent SDK (Python):**
```sh
pip install -e .
# then:
locus --palace ~/.locus --task "What K3s gotchas exist?"
```

**MCP server:**
```sh
pip install -e .
locus-mcp --palace ~/.locus
```

## Usage

```sh
# Query the palace
locus --palace ~/.locus --task "What toolchain conventions are set?"

# Run with metrics (for benchmarking)
locus --palace ~/.locus \
      --task "What K3s gotchas exist?" \
      --metrics-file tests/results/run.json

# JSON output
locus --palace ~/.locus --task "..." --json

# Run the MCP server (stdio transport)
locus-mcp --palace ~/.locus
# or: LOCUS_PALACE=~/.locus locus-mcp
```

## MCP Server

The `locus-mcp` command exposes four tools over the Model Context Protocol (stdio transport):

| Tool | Description |
|---|---|
| `memory_list` | Returns `INDEX.md` (no args) or lists a room's files |
| `memory_read` | Reads any file in the palace |
| `memory_write` | Atomically writes a file (guarded — cannot write to `_metrics/`, `sessions/`) |
| `memory_search` | Full-text search across the palace (ripgrep or Python fallback) |

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "locus": {
      "command": "locus-mcp",
      "args": ["--palace", "/path/to/palace"]
    }
  }
}
```

### Cursor / Zed

```json
{
  "mcp": {
    "servers": {
      "locus": {
        "command": "locus-mcp",
        "args": ["--palace", "/path/to/palace"]
      }
    }
  }
}
```

The MCP layer is recommended for MCP-capable clients. The skills remain the interface for Claude Code.
See `spec/mcp-server.md` for full architecture details and `docs/architecture.md` for diagrams.

## Structure

```
spec/           Convention definitions (size limits, index format, room layout, write modes)
templates/      Copy-paste templates for INDEX.md, rooms, session logs
skills/
  claude/       SKILL.md files for Claude Code + Agent SDK
  codex/        Codex-compatible skill files
  gemini/       Gemini CLI + GitHub Actions skill files
docs/
  architecture.md   Mermaid diagrams: palace structure, MCP server, agent interfaces, lifecycle
  benchmarks.md     Benchmark methodology, results, and charts
  img/              Generated SVG charts
  onboarding.md     Step-by-step agent onboarding guide
scripts/
  bench-mcp.py      40-case MCP integration benchmark (all 4 tools, safety, fidelity)
  bench-compare.py  Palace vs flat recall comparison (lines loaded, tool calls, recall)
  generate-charts.py  Regenerate docs/img/ charts from benchmark data
  try-mcp.py        Quick MCP smoke test
tests/
  fixtures/     Benchmark fixtures: palace + flat + flat-palace (same facts, three structures)
  run-benchmark.md  15-query benchmark procedure
  results/      Benchmark run outputs
locus/agent/    Python Agent SDK entrypoint (CLI + metrics collector)
locus/audit/    Palace health auditor (locus-audit CLI)
locus/feedback/ Inferred feedback signal classifier
locus/mcp/      MCP server (locus-mcp CLI)
```

## Benchmarking

Validates the core hypothesis: palace navigation loads less context than flat for
specific queries. Two benchmark approaches:

**MCP integration benchmark** — 40 test cases across all 4 tools, safety guards, and fidelity:
```sh
uv run scripts/bench-mcp.py
# Overall: 40/40 · avg 6.8ms · p95 15.8ms
```

**Palace vs flat recall comparison** — 9 recall scenarios, measures lines loaded and answer recall:
```sh
uv run scripts/bench-compare.py
# Palace: 822 lines / 9 found  ·  Flat: 1719 lines / 8 found  ·  −52% avg
```

See `docs/benchmarks.md` for charts and full results, and `tests/fixtures/README.md` for fixture details.

## Roadmap

| Milestone | Status | Focus |
|---|---|---|
| v0.1 - Foundation | ✅ Complete | Spec, conventions, size limits |
| v0.2 - Core Palace | ✅ Complete | Templates, skills, Agent SDK, benchmark |
| v0.3 - Performance Metrics | ✅ Complete | Context tracking, feedback command, suggestions |
| v0.4 - Self Evaluation | ✅ Complete | Palace audit skill, health reports, inferred feedback |
| v0.5 - MCP Server | ✅ Complete | MCP server with memory_list/read/write/search |

## License

TBD
