# Locus Style Guide for Gemini Code Assist

This guide defines the coding and documentation standards for the Locus project.
Apply these rules when reviewing pull requests or suggesting code changes.

---

## Project overview

Locus is a hierarchical markdown-based memory system for autonomous AI agents.
Its defining principle is: **load only what you need — never the whole palace.**
Every design decision should serve that constraint.

---

## Python

### Language version and tooling

- **Minimum Python version**: 3.11. Do not use features exclusive to 3.13+.
- **Package manager**: `uv`. Do not suggest `pip install` for development tasks;
  use `uv run` or `uv sync --extra dev`.
- **Linter**: `ruff`. Flag any code that would fail `uv run ruff check`.
- **Test runner**: `pytest` with `asyncio_mode = "auto"`. All async tests use
  `pytest-asyncio`; do not add `@pytest.mark.asyncio` manually.

### Style

- Use `from __future__ import annotations` at the top of every module.
- Type-annotate all function signatures (parameters and return type).
- Keep functions short and single-purpose. Prefer flat logic over deep nesting.
- Do not add `# type: ignore` without an explanatory comment.
- Use `pathlib.Path` for all filesystem operations; avoid raw string path manipulation.

### Imports

- Standard library first, then third-party, then local — separated by blank lines.
- Use absolute imports within the `locus` package; no relative imports except in
  `__init__.py` re-exports.
- `locus/security/` must not import from `locus/mcp/`. If a utility is needed by both,
  it belongs in `locus/utils.py`. This prevents circular dependencies.

### Error handling

- Raise `ValueError` for invalid caller input (e.g. bad paths, illegal arguments).
- Raise `PermissionError` for path traversal or write-blocked directory violations.
- Do not catch broad `Exception` without re-raising or logging with context.
- FastMCP tool errors return `isError=True` tool results — do not wrap tool calls
  in `try/except` expecting Python exceptions from guard violations.

### Security-sensitive code

The `locus/security/` module has extra-strict rules:

- `TaintTracker.session_tainted` is a **one-way latch**. Never add any method,
  parameter, or code path that clears or resets it within a session. This is the
  primary taint laundering defence.
- `auto_sign_writes` must default to `False` in `SigningConfig`. Changing this
  default opens a taint laundering vector.
- Do not change the signing protocol payload format (`locus-sig-v1\n...`) without
  bumping the protocol version string and versioning the sidecar schema.
- `safe_resolve()` and `assert_writable()` in `palace.py` must be called before
  every filesystem read/write. Do not bypass or shortcut them for performance.
- Write-blocked directories (`.sig/`, `.security/`, `sessions/`, `_metrics/`,
  `archived/`) are checked at **every depth** in the path, not just the top level.

---

## Tests

- Every new feature requires tests in `tests/unit/`. Every bug fix requires a
  regression test.
- New MCP tool behaviour → tests in `tests/unit/test_mcp.py`.
- New security behaviour → tests in `tests/unit/security/`.
- Use `tmp_path` (pytest fixture) for all filesystem tests; never use hardcoded
  paths like `/tmp/` directly.
- Test both the happy path and the failure path for all guard/safety functions.
- Do not mock `palace.py` safety functions (`safe_resolve`, `assert_writable`) in
  MCP tests — use a real `tmp_path` palace instead.
- After adding tests, confirm the total count is noted in the PR description.

---

## MCP tools and `palace.py`

- All five tools (`memory_list`, `memory_read`, `memory_write`, `memory_search`,
  `memory_batch`) have stable signatures defined in `spec/mcp-server.md`. Changes
  to tool signatures are **breaking changes** — flag any PR that modifies them.
- `memory_batch` reads up to 20 paths per call (`_MAX_BATCH_PATHS = 20`). Do not
  raise this limit without a corresponding benchmark and discussion.
- Read/write size limits are `_MAX_READ_BYTES = _MAX_WRITE_BYTES = 500_000`. Do not
  increase without justification.
- Palace resolution order: `--palace` arg → `LOCUS_PALACE` env → `.locus/` in CWD →
  `~/.claude/projects/<slug>/memory/` → `~/.locus/`. Do not alter this order.

---

## CLI entry points

- All three CLIs (`locus`, `locus-audit`, `locus-mcp`) use `argparse`. Do not
  migrate to Click or Typer — keep dependencies minimal.
- Every CLI must expose `--version` using `importlib.metadata.version("locus-mcp")`.
- `--security` is opt-in on both `locus` and `locus-mcp`. The security system must
  never activate automatically without the flag.
- Log to `sys.stderr` only; never to `sys.stdout` (stdout is the MCP wire protocol
  in stdio transport).

---

## Markdown and palace files

- `INDEX.md` must remain under 50 lines. Flag any PR that adds content to an
  existing `INDEX.md` that would push it over this limit.
- Room main files must remain under 200 lines. Flag any PR adding large blocks to
  room files.
- Session logs in `sessions/` are append-only and write-blocked via MCP — they are
  never edited after the session that created them.
- Use `<br/>` for line breaks in Mermaid node labels, not `\n`. GitHub's renderer
  does not support `\n` inside quoted labels.
- Scan all new markdown files for personal filesystem paths (e.g. `/home/<user>/`)
  before merging. Use generic references: "the palace root", "the locus source
  repository", "your home directory".

---

## SKILL.md files

- SKILL.md files in `skills/claude/`, `skills/codex/`, and `skills/gemini/` must
  remain agent-agnostic in their instructions (no Claude-specific APIs in codex/gemini
  variants, and vice versa).
- Do not rely on `allowed-tools` frontmatter for security — the Agent SDK ignores it.
  Tool access is controlled by the host `allowedTools` config.
- When adding a new skill to `skills/claude/`, create matching variants in
  `skills/codex/` and `skills/gemini/` in the same PR.
- Install all skills with `make install-skills` from the repo root.

---

## Documentation and changelog

Every PR that merges to `main` must include:

- A `CHANGELOG.md` entry using the format in `CONTRIBUTING.md` section 9.
- `README.md` updates if new CLIs, flags, or skills are added.
- Wiki updates if the change affects installation, CLI options, or configuration.
- Cross-agent skill updates (`skills/codex/`, `skills/gemini/`) if a Claude skill
  is added or changed.

Flag any PR that modifies user-facing behaviour without updating the docs.

---

## Dependencies

- Runtime dependencies are intentionally minimal. Do not add new runtime deps
  without a strong justification and an issue/discussion.
- `uv.lock` must be committed and kept in sync with `pyproject.toml`. Flag any PR
  where `pyproject.toml` changed but `uv.lock` was not updated.
- `fastmcp`, `cryptography`, `uvicorn`, and `anyio` are current runtime deps.
  `matplotlib` is a dev-only dep. Keep this separation.

---

## What not to flag

Do not raise issues for:

- The `example-palace/` directory — it contains intentionally minimal template
  content and is not production code.
- `tests/fixtures/` — fixture content is minimal by design for benchmark purposes.
- Generated files: `uv.lock`, `docs/bench/*.json`, `docs/img/*.svg`.
