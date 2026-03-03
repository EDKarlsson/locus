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
```

## Structure

```
spec/           Convention definitions (size limits, index format, room layout, write modes)
templates/      Copy-paste templates for INDEX.md, rooms, session logs
skills/
  claude/       SKILL.md files for Claude Code + Agent SDK
  codex/        Codex-compatible skill files
  gemini/       Gemini CLI + GitHub Actions skill files
docs/           Onboarding guide and reference docs
tests/
  fixtures/     Benchmark fixtures: flat vs palace (same facts, two structures)
  run-benchmark.md  15-query benchmark procedure
  results/      Benchmark run outputs
locus/agent/    Python Agent SDK entrypoint (CLI + metrics collector)
```

## Benchmarking

Validates the core hypothesis: palace navigation loads less context than flat for
specific queries. See `tests/fixtures/README.md` for the numbers.

```sh
# Run a benchmark query against both fixtures
locus --palace tests/fixtures/palace --task "What is the K3s API server endpoint?" \
      --metrics-file tests/results/palace-A1.json

locus --palace tests/fixtures/flat --task "What is the K3s API server endpoint?" \
      --metrics-file tests/results/flat-A1.json
```

See `tests/run-benchmark.md` for the full 15-query set and results template.

## Roadmap

| Milestone | Status | Focus |
|---|---|---|
| v0.1 - Foundation | ✅ Complete | Spec, conventions, size limits |
| v0.2 - Core Palace | ✅ Complete | Templates, skills, Agent SDK, benchmark |
| v0.3 - Performance Metrics | Planned | Context tracking, feedback command, suggestions |
| v0.4 - Self Evaluation | Planned | Palace audit skill, health reports |
| v0.5 - MCP Server | Planned | Optional MCP layer with search |

## License

TBD
