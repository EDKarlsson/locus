# Changelog

## v0.9.0 — 2026-03-11

### Ed25519 Security System — prompt injection defense for AI agents

Adds a cryptographic trust layer that makes injected content in memory files
cryptographically distinguishable from operator-authorized content. Enabled
with `--security` on both the Agent SDK and MCP server.

**Architecture — 5-layer stack:**

```
[Operator] --signs--> [Memory files + System prompt]
                              |
               [SecurityMiddleware]  ← PreToolUse / PostToolUse hooks
                              |
            Tags output: [TRUSTED] | [DATA] | [CRITICAL-DATA]
                              |
                       [Agent LLM]  ← nonce embedded in signed system prompt
```

**New package: `locus/security/`**

- `keys.py` — Ed25519 keypair generation, PKCS8/AES-256-CBC storage, rotation.
  `locus-security init-keys --palace <path>` creates `.security/keys/active.pem`
  + `active.pub`. `rotate-keys` archives the current public key to `retired/` and
  generates a fresh active pair. The private key is never retained after rotation.
- `signing.py` — `sign_file()` / `verify_file()` using Ed25519 sidecar files
  (`.sig/<filename>.sig`, YAML). Canonical payload: `locus-sig-v1\n<palace_slug>\n<rel_path>\n<signed_at>\n<sha256_hex>`.
  Content normalised to LF + BOM-stripped before hashing. `sign_system_prompt()`
  embeds a verifiable `SECURITY CONTEXT` block in the agent system prompt.
- `nonce.py` — `generate_session_nonce()` (HMAC-SHA256 over 32-byte random seed,
  32-char URL-safe base64). Injected into system prompt once per session;
  exfiltration detected in every tool output unconditionally.
- `taint.py` — `TaintTracker` with sticky propagation: TRUSTED → AUDITED →
  TAINTED. `classify_content()` checks for injection patterns and nonce.
  Nonce detection always escalates to TAINTED regardless of signature status.
- `config.py` — `SecurityConfig` from `locus-security.yaml`. Three criticality
  levels: `CRITICAL` (block), `AUDITED` (tag + log), `PERMISSIVE` (pass-through).
  Fail-closed: missing config or keys at startup raises `FileNotFoundError` —
  never silently degrades to unsecured mode.
- `middleware.py` — `SecurityMiddleware` registering `PreToolUse` / `PostToolUse`
  hooks. Pre-hook verifies file signatures and blocks CRITICAL violations.
  Post-hook injects trust tags and scans unconditionally for nonce exfiltration.
  `post_write_hook()` auto-signs new files after every Write.
- `__init__.py` — Public surface: `build_security_context()`, `SecurityContext`,
  `AuditEntry`.

**CLI integration**

- `locus --security` — Agent SDK run with full middleware stack. Fails at startup
  if `locus-security.yaml` or keys are absent.
- `locus-mcp --security` — MCP server with `_SecurityVerifier` verifying every
  `memory_read`, `memory_list`, and `memory_batch` result; auto-signing every
  `memory_write`.
- `locus-security init-keys`, `locus-security rotate-keys`, `locus-security sign-all`
  — key management CLI.

**Safety guard updates (`mcp/palace.py`)**

- `.sig/` and `.security/` added to `_WRITE_BLOCKED_DIRS` — agents cannot
  overwrite or forge sidecar files or key material via MCP tools.

**Skills and templates**

- `skills/claude/locus-security/SKILL.md` — agent-facing conventions: trust tag
  recognition, nonce discipline, injection pattern recognition (fake System:
  blocks, embedded tool calls), write discipline (never launder `[DATA]` content
  verbatim), incident reporting to `_security/incidents/`.
- `templates/locus-security.yaml` — fully annotated configuration template.

**Docs**

- `docs/security.md` — comprehensive reference: threat model, five-layer stack
  flowchart, secured-read and auto-sign write sequence diagrams, key management,
  signature protocol, trust tag table, full config reference, and design decision
  rationale (Ed25519 vs HMAC, sidecar vs inline, per-session nonce, fail-closed,
  sticky taint).
- `docs/architecture.md` — added Security Layer section with Mermaid flowchart.
- `docs/onboarding.md` — added section 8 "Security (optional hardening)" with
  4-step setup guide.
- `docs/benchmarks.md` — updated with three-way comparison: v0.8.0, v0.9.0-base,
  v0.9.0-security. Security overhead is ≤ +1.4 ms per category.

**Performance (see `docs/benchmarks.md` for full analysis)**

- Baseline (no security): 45/45, avg 4.7 ms, p95 13.8 ms
- With `--security`: 45/45, avg 4.9 ms (+0.2 ms, +4%), p95 10.3 ms
- Highest overhead: `write` +1.4 ms (+38%) and `batch` +1.1 ms (+35%)
  — both from Ed25519 sign/verify per file. Safety guards are unaffected
  (+0.1 ms — rejections still short-circuit before crypto).

**Tests**

- `tests/unit/security/` — 5 test modules covering all layers:
  `test_config.py`, `test_keys.py`, `test_signing.py`, `test_nonce.py`,
  `test_taint.py`
- `tests/unit/security/test_review_fixes.py` — 13 regression tests for all
  P1/P2 review findings: fail-open removal, coverage gaps in `memory_list` /
  `memory_batch`, path-traversal anchoring, unconditional nonce detection,
  `embed_nonce` flag respected

**New dependency:** `cryptography>=41.0`, `pyyaml>=6.0`

---

## v0.8.0 — 2026-03-03

### Auto-memory bridge + `memory_batch` tool

**Auto-memory bridge** — `locus-mcp` now detects Claude Code's auto-memory
directory automatically when started from a project directory with no explicit
`--palace` argument. It derives the Claude Code project slug by replacing `/`
with `-` in the CWD path, then checks `~/.claude/projects/<slug>/memory/`.
If that directory exists it becomes the palace root. Zero configuration needed.
Priority slot: `.locus/` > **auto-memory** > `~/.locus/`.

**`memory_batch` tool** — new MCP tool that reads up to 20 palace files in a
single call. Sections are joined by `---`, each headed by `## <path>`. Missing
files, directories, and path-traversal violations are noted inline (never
raised as exceptions), so partial results are always returned for valid calls.
Raises `ValueError` only for invalid arguments (more than 20 paths). Path
headers are sanitized to strip embedded newlines and prevent Markdown injection.
Designed for research agents that need several rooms at startup.

**Spec** — `spec/mcp-server.md` updated with `memory_batch` in the Tools table,
an "Auto-Memory Bridge" section (slug derivation rule + log signal), and a
"Simplify Integration Pattern" documenting the `code-patterns` palace room
workflow for persistent project-specific context.

- `feat(mcp/palace)`: `_slug_from_path`, `find_auto_memory`, updated `find_palace` priority
- `feat(mcp/server)`: `memory_batch` tool, `_MAX_BATCH_PATHS = 20`
- +15 unit tests (`TestFindAutoMemory`, `TestMemoryBatch`) — 201 tests total

---

## v0.7.1 — 2026-03-03

### Fix: allowed hosts for SSE reverse-proxy deployments

FastMCP 1.26.0 enables DNS rebinding protection by default, restricting allowed `Host`
headers to loopback (`127.0.0.1:*`, `localhost:*`, `[::1]:*`). Requests from Tailscale
or Kubernetes ingress (e.g. `locus.oryx-tegu.ts.net`, `locus.locus.svc.cluster.local`)
were rejected with `421 Misdirected Request`.

- `fix(mcp)`: Added `LOCUS_ALLOWED_HOSTS` env var — comma-separated hostnames (using
  FastMCP `:*` port wildcard) appended to the loopback defaults before SSE server start
- `fix(mcp)`: Bumped `mcp>=1.26.0` floor (`TransportSecuritySettings` was added in 1.26.0)
- +3 unit tests (`TestSseAllowedHosts`) — 186 tests total

---

## v0.7.0 — 2026-03-03

### SSE transport + Docker image for network deployments

Exposes `locus-mcp` as a network service (SSE transport) suitable for homelab K8s
clusters, n8n/Windmill automation, and any environment where multiple clients need a
shared palace over HTTP.

**CLI change**

- Added `--transport {stdio,sse}` flag to `locus-mcp`. Default is `stdio` (unchanged).
  SSE mode starts a uvicorn server instead of reading from stdin.

**Auth**

- `BearerAuthMiddleware` — raw ASGI middleware (not `BaseHTTPMiddleware` which buffers
  response bodies and breaks long-lived SSE streams). Set `LOCUS_API_KEY` to enable.
  Responses include `WWW-Authenticate: Bearer realm="locus-mcp"` on 401.

**Environment variables (SSE mode)**

| Variable | Default | Purpose |
|---|---|---|
| `FASTMCP_HOST` | `127.0.0.1` | Bind address — set to `0.0.0.0` for container deployments |
| `FASTMCP_PORT` | `8000` | Bind port |
| `LOCUS_API_KEY` | unset | Bearer token for auth (recommended) |

**Dockerfile**

```dockerfile
FROM python:3.12-slim
ARG LOCUS_MCP_VERSION="0.7.1"
RUN pip install --no-cache-dir "locus-mcp==${LOCUS_MCP_VERSION}"
ENTRYPOINT ["locus-mcp"]
```

Image published to `ghcr.io/edkarlsson/locus-mcp:0.7.1`.

**Dependencies**

- `uvicorn>=0.30` promoted from optional to core dependency

**Security fixes (from code review)**

- `fix(mcp/server)`: rg argument injection — added `"--"` separator before user query
  in `memory_search` subprocess args (prevents query starting with `--` from injecting
  ripgrep flags)
- `fix(mcp/main)`: `secrets.compare_digest()` for constant-time token comparison

---

## v0.6.2 — 2026-03-03

### Auto-bootstrap palace on first start

`find_palace()` now creates `~/.locus/` with `INDEX.md`, `global/`, and `projects/`
subdirectories when the default palace doesn't exist — instead of raising an error.
Explicit `--palace` and `LOCUS_PALACE` paths still raise if missing (those are
configuration errors, not first-run). Updated test: `test_no_palace_raises` →
`test_no_palace_bootstraps_home_locus`.

---

## v0.6.1 — 2026-03-02

### MCP Registry ownership tag

- Added `<!-- mcp-name: io.github.EDKarlsson/locus -->` to README.md (required by the
  Official MCP Registry PyPI ownership validation)
- Updated `server.json` with correct schema fields: `repository.source: "github"` and
  `packages[0].transport.type: "stdio"` — passes registry validation

---

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
- **PyPI**: `locus-mcp` v0.6.0 published at https://pypi.org/project/locus-mcp/

**CI fix**
- `fix(ci)`: `publish.yml` environment name corrected to `uv` to match the PyPI
  OIDC trusted publisher config; tag re-pointed to the fixed commit before re-publish

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
