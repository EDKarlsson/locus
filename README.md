# Locus

<!-- mcp-name: io.github.EDKarlsson/locus -->

[![CI](https://github.com/EDKarlsson/locus/actions/workflows/ci.yml/badge.svg)](https://github.com/EDKarlsson/locus/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/locus-mcp.svg)](https://pypi.org/project/locus-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

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

See the [wiki](https://github.com/EDKarlsson/locus/wiki) for full documentation.

---

## Quick start

```sh
# Install
pip install locus-mcp
# or: uvx locus-mcp --palace ~/.locus  (no install needed)

# Create a palace from the example template
cp -r example-palace ~/.locus
# Edit ~/.locus/INDEX.md to describe your palace

# Run the MCP server
locus-mcp --palace ~/.locus
# or: LOCUS_PALACE=~/.locus locus-mcp
```

---

## Installation

### MCP server (recommended for MCP-capable clients)

```sh
pip install locus-mcp
```

Or run without installing using `uvx`:

```sh
uvx locus-mcp --palace ~/.locus
```

### Claude Code skills

```sh
cp -r skills/claude/locus ~/.claude/skills/locus
cp -r skills/claude/locus-consolidate ~/.claude/skills/locus-consolidate
```

### Codex

```sh
cp -r skills/codex/locus ~/.codex/skills/locus
cp -r skills/codex/locus-consolidate ~/.codex/skills/locus-consolidate
```

### Gemini

Reference `skills/gemini/locus/SKILL.md` from your `.gemini/` directory
or a GitHub Actions workflow (see `skills/gemini/`).

### Agent SDK (Python)

```sh
pip install locus-mcp
locus --palace ~/.locus --task "What toolchain conventions are set?"
```

---

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

Or using `uvx` (no install required):

```json
{
  "mcpServers": {
    "locus": {
      "command": "uvx",
      "args": ["locus-mcp", "--palace", "/path/to/palace"]
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

### Environment variable

All clients support `LOCUS_PALACE` as an alternative to `--palace`:

```sh
export LOCUS_PALACE=~/.locus
locus-mcp
```

See [MCP Server Configuration](https://github.com/EDKarlsson/locus/wiki/MCP-Server-Configuration)
for the full client setup guide and `spec/mcp-server.md` for architecture details.

---

## Benchmarks

Palace navigation loads **52% fewer context lines** than flat memory for specific queries,
while maintaining full recall. Session-only queries (recent work not yet consolidated)
are accessible only via the palace.

```
Palace: 822 lines / 9 queries found   avg  91 lines/query · 3.2 calls
Flat:  1719 lines / 8 queries found   avg 191 lines/query · 2.0 calls
```

See [`docs/benchmarks.md`](docs/benchmarks.md) for charts and full methodology.

---

## Structure

```
example-palace/   Copy-paste palace template to get started
spec/             Palace convention definitions:
  index-format.md       INDEX.md rules and routing
  room-conventions.md   Room structure and naming
  size-limits.md        Context budget thresholds
  write-modes.md        Session logs vs canonical edits
  mcp-server.md         MCP server architecture and safety model
  metrics-schema.md     Run metrics JSON schema
  audit-algorithm.md    Palace health scoring
  health-report-format.md  Audit report structure
  inferred-feedback.md  Disagreement signal classification
templates/        Copy-paste templates for INDEX.md, rooms, session logs
skills/
  claude/         SKILL.md files for Claude Code + Agent SDK
  codex/          Codex-compatible skill files
  gemini/         Gemini CLI + GitHub Actions skill files
docs/
  architecture.md       Mermaid diagrams
  benchmarks.md         Benchmark results and charts
  onboarding.md         Step-by-step agent onboarding
scripts/
  bench-mcp.py          40-case MCP integration benchmark
  bench-compare.py      Palace vs flat recall comparison
  generate-charts.py    Regenerate docs/img/ charts
locus/agent/      Python Agent SDK (CLI + metrics)
locus/audit/      Palace health auditor (locus-audit CLI)
locus/feedback/   Inferred feedback classifier
locus/mcp/        MCP server (locus-mcp CLI)
```

---

## Roadmap

| Milestone | Status | Focus |
|---|---|---|
| v0.1 - Foundation | ✅ Complete | Spec, conventions, size limits |
| v0.2 - Core Palace | ✅ Complete | Templates, skills, Agent SDK, benchmark |
| v0.3 - Performance Metrics | ✅ Complete | Context tracking, feedback, suggestions |
| v0.4 - Self Evaluation | ✅ Complete | Palace audit, health reports, inferred feedback |
| v0.5 - MCP Server | ✅ Complete | MCP server with memory_list/read/write/search |
| v0.6 - Public release | ✅ Complete | Benchmarks, docs, CI, PyPI |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, test instructions, and PR guidelines.

## License

[MIT](LICENSE)
