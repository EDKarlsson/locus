# Contributing to Locus

Thanks for your interest in contributing. Locus is a small, focused project —
contributions that stay true to its core design principle are most welcome:

> **Load only what you need. Never the whole palace.**

---

## Getting started

```sh
git clone https://github.com/EDKarlsson/locus
cd locus
uv sync --extra dev
```

Run the tests:

```sh
uv run pytest tests/unit/ -v
# 175 tests, all should pass
```

Run the MCP integration benchmark (sanity-check the live server):

```sh
uv run scripts/bench-mcp.py
# Expected: 40/40 pass
```

---

## What to contribute

**Good fits:**
- Bug fixes in `locus/mcp/`, `locus/audit/`, or `locus/agent/`
- New MCP tool behaviours (with tests in `tests/unit/test_mcp.py`)
- Improvements to the benchmark harness (`scripts/`)
- Skill files for new agent runtimes (new `skills/<runtime>/` directory)
- Documentation improvements

**Please discuss first (open an issue):**
- Changes to the palace convention specs (`spec/`) — these are the shared
  contract between agents and shouldn't change lightly
- New CLI entry points or package restructuring
- Breaking changes to `palace.py` safety model

---

## Code style

- Python 3.11+, type hints on all public functions
- `uv run` for all tool invocations (no bare `pytest`, `python`, etc.)
- Tests live in `tests/unit/` and follow the existing fixture patterns
- No external test dependencies beyond `pytest` + `pytest-asyncio`

---

## Submitting a PR

1. Fork the repo, create a branch from `main`
2. Make your change with tests
3. Ensure `uv run pytest tests/unit/` passes
4. Open a PR — describe what you changed and why
5. PRs are squash-merged into `main`

---

## Design constraints

These are load-bearing — please don't work around them:

| Constraint | Reason |
|---|---|
| `INDEX.md` ≤ 50 lines | Always loaded; must stay small |
| Room files ≤ 200 lines | Context budget per room |
| Sessions write-only via MCP | Consolidation happens explicitly, not automatically |
| Path traversal strictly rejected | Local filesystem access must be scoped to palace |
| stdio is the default MCP transport | Use `locus-mcp` without `--transport` for all local integrations (Claude Desktop, Claude Code, Codex, Gemini). SSE transport (`--transport sse`) is opt-in for network deployments and requires `FASTMCP_HOST` to be set explicitly — the default bind address is `127.0.0.1`. |

See `spec/` for the full convention definitions.
