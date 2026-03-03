# Security PR Review Report (March 3, 2026)

## Executive Summary

This security-focused review found **no known dependency CVEs** in the audited environment as of **2026-03-03** (`pip-audit`), but identified **four code/config attack surfaces** that should be addressed before release hardening:

1. Regex-based DoS risk in `memory_search` Python fallback.
2. Unbounded MCP read/write payload sizes enabling resource-exhaustion DoS.
3. Environment/PATH process-hijack risk around `rg` invocation.
4. Prompt-injection-to-shell risk in agent mode when used with untrusted palace content.

No direct path traversal vulnerability was found; existing path guards are solid (`safe_resolve`).

## Scope and Method

- Branch: `audit/repo-audit`
- Focus: vulnerabilities, exploitability, attack vectors, and known dependency issues
- Methods:
  - Manual code review (MCP server, agent runtime, workflows)
  - Static scanner: Bandit
  - Dependency scanner: pip-audit
- Artifacts:
  - `docs/audits/artifacts/2026-03-03-bandit.json`
  - `docs/audits/artifacts/2026-03-03-pip-audit.txt`

## Positive Security Controls Observed

- Path traversal defense: `safe_resolve()` resolves and enforces path containment (`locus/mcp/palace.py:58-72`).
- Write-guarded system directories and extension allowlist (`locus/mcp/palace.py:75-90`).
- MCP transport model is stdio/local by design (`spec/mcp-server.md:12-17`).
- Publish flow uses PyPI trusted publishing with OIDC (`.github/workflows/publish.yml:13-29`).

## Findings

### SEC-001 (High): Regex DoS in Python fallback search path

- Severity: High
- Location: `locus/mcp/server.py:248-267`
- Evidence:
  - Untrusted `query` is compiled as a regex: `pattern = re.compile(query, re.IGNORECASE)` (`:251`)
  - Pattern is executed against file content in nested loops (`:258-267`)
  - No regex timeout, no complexity guard, no literal-mode fallback.
- Attack vector:
  - If `rg` is unavailable at runtime, attacker-controlled query can trigger catastrophic backtracking and tie up CPU.
- Impact:
  - Denial of service for MCP operations in constrained or multi-tenant host environments.
- Fix:
  - Prefer literal search fallback (`re.escape(query)` or plain substring matching), or use a regex engine with timeout/linear guarantees.
  - Enforce max query length.
- Mitigation:
  - Keep `rg` installed and fail closed if unavailable instead of regex fallback.
- False-positive notes:
  - This requires fallback path activation (when `rg` is missing).

### SEC-002 (Medium): Unbounded content size in MCP read/write operations

- Severity: Medium
- Location:
  - `locus/mcp/server.py:102-104` (full file read to memory)
  - `locus/mcp/server.py:122-139` (arbitrary-size write content)
- Evidence:
  - `memory_read` returns full file contents with no max-size checks.
  - `memory_write` accepts full `content` and writes it atomically without size limits.
- Attack vector:
  - Malicious or compromised client can request very large reads/writes to consume memory/disk.
- Impact:
  - Local resource exhaustion (disk fill, memory pressure, slowdowns), degraded service availability.
- Fix:
  - Add configurable maximum read/write byte limits and reject oversized operations.
  - Optionally stream large reads or return truncated output with explicit metadata.
- Mitigation:
  - Run under filesystem quotas and process-level resource controls.
- False-positive notes:
  - Risk level depends on how trusted MCP clients are in your deployment.

### SEC-003 (Low): PATH hijack risk for `rg` executable resolution

- Severity: Low
- Location: `locus/mcp/server.py:192-206`
- Evidence:
  - `subprocess.run([...])` executes `"rg"` via PATH lookup (`:194`), not absolute path.
  - Bandit flags `B607` in artifact (`docs/audits/artifacts/2026-03-03-bandit.json`).
- Attack vector:
  - If an attacker can alter runtime PATH/environment, a malicious `rg` binary could be executed.
- Impact:
  - Potential arbitrary code execution under process privileges in compromised runtime environments.
- Fix:
  - Resolve and pin absolute executable path (`shutil.which("rg")` once at startup, validate location) or vendor controlled binary path.
- Mitigation:
  - Harden runtime environment: sanitized PATH, locked service unit env.
- False-positive notes:
  - Requires environment compromise or unsafe launch context.

### SEC-004 (Medium): Prompt-injection-to-shell exposure in agent mode

- Severity: Medium
- Location: `locus/agent/config.py:6` and `locus/agent/config.py:31-37`
- Evidence:
  - Agent is granted `Bash` in `ALLOWED_TOOLS` (`:6`).
  - Runtime uses `permission_mode="acceptEdits"` (`:36`) and autonomous query loop in agent CLI.
- Attack vector:
  - Untrusted palace content (or untrusted task input) can socially engineer tool use into shell execution.
- Impact:
  - Host command execution risk if the agent follows malicious instructions.
- Fix:
  - Provide a hardened mode that excludes `Bash` by default (opt-in only).
  - Restrict allowed tools by trust level and use explicit allowlists for command classes.
- Mitigation:
  - Treat palace content as trusted-only, or isolate runs in a locked sandbox/container.
- False-positive notes:
  - Risk is contextual; trusted local workflows may accept this tradeoff.

### SEC-005 (Low): GitHub Actions supply-chain hardening gap (unpinned action refs)

- Severity: Low
- Location:
  - `.github/workflows/ci.yml:18` and `.github/workflows/ci.yml:21`
  - `.github/workflows/publish.yml:17`, `:20`, `:28`
- Evidence:
  - Actions are pinned to mutable tags (`@v4`, `@release/v1`) rather than commit SHAs.
- Attack vector:
  - Upstream action compromise/tag move can inject malicious code into CI/publish jobs.
- Impact:
  - CI integrity and release pipeline trust degradation.
- Fix:
  - Pin third-party actions to immutable commit SHAs and update via controlled process.
- Mitigation:
  - Enable GitHub dependency review/renovation for action SHAs.
- False-positive notes:
  - Common pattern in many repos, but weaker than SHA pinning.

## Known Exploits / Dependency Status

- `pip-audit` output (captured 2026-03-03): **No known vulnerabilities found** for resolved dependencies.
- Note: local package `locus-mcp` is skipped by pip-audit because it is not fetched as a published dependency in this context (`docs/audits/artifacts/2026-03-03-pip-audit.txt`).

## Scanner Summary

- Bandit:
  - 4 findings, all low severity (`B404`, `B110`, `B607`, `B603`)
  - Mostly advisory around subprocess usage and generic exception handling
  - Artifact: `docs/audits/artifacts/2026-03-03-bandit.json`
- pip-audit:
  - No known dependency vulnerabilities detected
  - Artifact: `docs/audits/artifacts/2026-03-03-pip-audit.txt`

## Prioritized Remediation Plan

1. Implement safe search fallback behavior (`SEC-001`) and add regression tests for malicious regex payloads.
2. Add MCP read/write size limits and error semantics for oversized payloads (`SEC-002`).
3. Add hardened agent runtime mode without `Bash` for untrusted sources (`SEC-004`).
4. Pin external GitHub Actions to SHAs (`SEC-005`).
5. Hard-pin/validate `rg` path at startup (`SEC-003`).

## PR Review Recommendation

Request changes for `SEC-001` and `SEC-002` before merge to reduce practical DoS exposure; track `SEC-003` to `SEC-005` as follow-up hardening if this PR is release-critical.
