Locus is a hierarchical markdown memory system for AI agents. Core invariant: **load only what you need**. All changes must preserve minimal-context semantics and agent-agnostic compatibility.

## Security invariants — flag any violation

- `TaintTracker.session_tainted` is a one-way latch. Flag any code that clears, resets, or conditionally bypasses it within a session. There is no safe in-session reset.
- `auto_sign_writes` must default to `False` in `SigningConfig`. A `True` default enables taint laundering.
- `safe_resolve()` and `assert_writable()` in `palace.py` must be called before every filesystem read/write. Flag any path that bypasses them, including new helper functions.
- Write-blocked dirs (`.sig/`, `.security/`, `sessions/`, `_metrics/`, `archived/`) must be checked at every depth in the path, not just `parts[0]`.
- `locus/security/` must not import from `locus/mcp/`. Shared utilities belong in `locus/utils.py` to avoid circular dependencies.
- Signing protocol payload (`locus-sig-v1\n<slug>\n<path>\n<signed_at>\n<sha256>`) is versioned. Flag any modification to this format without a protocol version bump.

## MCP tool contracts

The five tool signatures (`memory_list`, `memory_read`, `memory_write`, `memory_search`, `memory_batch`) are stable — changes to parameter names, types, or return shapes are breaking. FastMCP guard errors return `isError=True` tool results, not Python exceptions. Flag `try/except` around tool calls that expect exceptions from guard violations.

## Python correctness

- Flag `((var++))` in bash scripts running under `set -e` — post-increment returns the old value, which exits on zero. Use `var=$((var + 1))` instead.
- Flag broad `except Exception` without re-raise or meaningful log context.
- Flag raw string path manipulation — all paths must use `pathlib.Path`.
- Flag `# type: ignore` without an explanatory comment.
- Flag manual `@pytest.mark.asyncio` — the project uses `asyncio_mode = "auto"` globally.
- Flag any write to `sys.stdout` in server code — stdout is the MCP wire protocol in stdio transport. All logging must use `sys.stderr`.

## Tests

Flag PRs that add or change behaviour without tests. Specifically:
- New MCP tool behaviour missing tests in `tests/unit/test_mcp.py`
- New security behaviour missing tests in `tests/unit/security/`
- Tests that mock `safe_resolve` or `assert_writable` instead of using a real `tmp_path` palace — mocking safety guards defeats the test
- Missing failure-path tests for any guard or boundary function

## CLI and public API

- Flag any CLI missing `--version` backed by `importlib.metadata.version("locus-mcp")`.
- `--security` must remain opt-in. Flag any code path that activates the security system without the flag being set.
- Flag changes to MCP tool signatures — these are public API and require a major version bump.

## Dependencies

Flag any new entry in the `[project.dependencies]` section of `pyproject.toml` without a clear justification. Current runtime deps: `fastmcp`, `cryptography`, `uvicorn`, `anyio`. `matplotlib` is dev-only — flag if it migrates to runtime. Always flag `pyproject.toml` changes where `uv.lock` was not updated in the same commit.

## Size limits

Flag additions to `INDEX.md` that push it past 50 lines, and room main files approaching 200 lines. These limits preserve the context budget the system is designed around.

## Do not flag

`example-palace/`, `tests/fixtures/`, `uv.lock`, `docs/bench/*.json`, `docs/img/*.svg` — template, fixture, or generated content.
