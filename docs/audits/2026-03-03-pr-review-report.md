# PR Review Report: Locus Audit Baseline

## Review Metadata

- Date (UTC): 2026-03-03T04:15:07Z
- Branch reviewed: `audit/repo-audit`
- Repository: `EDKarlsson/locus`
- Reviewer scope: code quality, spec conformance, CI/build/test health, release readiness

## Decision

**Request changes before merge** due to spec-conformance issues in the audit subsystem.

## Findings (Ordered by Severity)

### 1) High: stale-room scoring does not implement 90-day recency rule

- Evidence:
  - Spec requires stale when no metrics in last 90 days (or no metrics): `spec/audit-algorithm.md:83`
  - Implementation only checks for absence of enrichment data:
    - `locus/audit/scanner.py:169-171`
- Why this matters:
  - Rooms with only old metrics are not classified stale, reducing maintenance signal quality.
  - Audit output diverges from documented behavior.
- Recommended change:
  - Track metric recency per room and mark stale when latest touching run is older than 90 days.
  - Keep current "no metrics at all" behavior as part of the same rule.
- Test gap:
  - Add tests for both:
    - metrics present but all older than 90 days -> `stale`
    - recent metrics present -> not stale

### 2) Medium: degraded retrieval-depth rule is applied to all run types, not Type A only

- Evidence:
  - Spec scope: Type A only for `retrieval_depth_avg > 3.5`: `spec/audit-algorithm.md:76`
  - Implementation averages touching runs without `query_type` filtering: `locus/audit/scanner.py:121-127`
  - Degraded scoring then triggers globally: `locus/audit/scanner.py:160-162`
- Why this matters:
  - Non-Type-A workloads (B/C/D) can trigger degraded actions intended for specific-fact lookup quality.
- Recommended change:
  - Compute retrieval-depth signal for Type A runs only, or maintain separate averages per query type and score against Type A.
- Test gap:
  - Add a test where only Type B/C/D runs exceed 3.5 and confirm room is not degraded for this rule.

### 3) Medium: unstructured-directory remediation action is missing

- Evidence:
  - Spec requires action when unstructured dirs are present: `spec/audit-algorithm.md:127`
  - Current implementation only surfaces count in summary:
    - `locus/audit/main.py:47-55`
    - `locus/audit/main.py:58-81`
- Why this matters:
  - The report indicates a structural issue but does not produce an actionable task.
- Recommended change:
  - When `unstructured_dirs > 0`, append a warning action item describing expected remediation.
- Test gap:
  - Add integration test asserting the action item exists when an orphan `.md` directory is discovered.

### 4) Medium: audit report filename format diverges from documented pattern

- Evidence:
  - Spec format: `audit-YYYY-MM-DDTHHMMSSZ.*`:
    - `spec/health-report-format.md:4`
    - `spec/health-report-format.md:149`
  - Current code constructs stem with compact date and a dot before `Z`: `locus/audit/report.py:151-152`
  - Reproduction output: `audit-20260303T041423.Z.md`
- Why this matters:
  - Any downstream tool/parser expecting documented filenames can miss reports.
- Recommended change:
  - Generate stem from canonical UTC format without separators mismatch:
    - `YYYY-MM-DDTHHMMSSZ` (for example: `2026-03-03T041423Z`)
- Test gap:
  - Add assertion on filename regex in `TestWriteReports`.

### 5) Low: duplicated session-log filtering creates avoidable ambiguity

- Evidence:
  - `logs` is computed, then recomputed with different logic immediately after:
    - `locus/audit/scanner.py:71-77`
- Why this matters:
  - Harder to reason about and maintain; raises future regression risk.
- Recommended change:
  - Keep a single authoritative filter path and remove dead intermediate computation.

### 6) Low: dead/incorrect helper in report formatter

- Evidence:
  - `_fmt()` appears unused and contains unreachable condition (`"rate" in ""`):
    - `locus/audit/report.py:38-45`
  - No call sites found in tree.
- Why this matters:
  - Signals missing coverage around formatting utilities and adds noise.
- Recommended change:
  - Remove `_fmt()` or wire it correctly with targeted tests.

## Verification Summary

- Unit tests: `uv sync --extra dev && uv run pytest tests/unit/ -v --tb=short` -> **175 passed**
- Package build: `uv build` -> **sdist + wheel built**
- CLI smoke:
  - `uv run locus --help`
  - `uv run locus-mcp --help`
  - `uv run locus-audit --help`
  - All entry points load successfully
- CI workflows reviewed:
  - `.github/workflows/ci.yml`
  - `.github/workflows/publish.yml`

## Risk Assessment

- Functional runtime risk: **Low-Medium** (core CLIs and tests are healthy)
- Governance/spec risk: **Medium-High** (audit behavior differs from contract in multiple places)
- Release risk: **Medium** if report consumers rely on spec-defined semantics and filenames

## Suggested PR Review Comment (Ready to Post)

```markdown
Requesting changes on this PR due to audit subsystem spec drift.

### Findings
1. **High** — stale scoring does not implement "no metrics in last 90 days" (`spec/audit-algorithm.md:83` vs `locus/audit/scanner.py:169-171`).
2. **Medium** — retrieval-depth degraded threshold is applied to all runs instead of Type A only (`spec/audit-algorithm.md:76`, `locus/audit/scanner.py:121-127`, `160-162`).
3. **Medium** — unstructured directory count is reported but no remediation action item is emitted (`spec/audit-algorithm.md:127`, `locus/audit/main.py:47-55`, `58-81`).
4. **Medium** — audit report filename format diverges from documented pattern (`spec/health-report-format.md:4`, `149` vs `locus/audit/report.py:151-152`).
5. **Low** — duplicate session log filter logic in `collect_room_signals` (`locus/audit/scanner.py:71-77`).
6. **Low** — dead/incorrect `_fmt()` helper (`locus/audit/report.py:38-45`).

### Validation Performed
- `uv sync --extra dev && uv run pytest tests/unit/ -v --tb=short` (175 passed)
- `uv build` (sdist and wheel built)
- `uv run locus --help`, `locus-mcp --help`, `locus-audit --help` (all pass)

Please address the 4 medium/high items before merge.
```

## Proposed Fix Order

1. Implement stale recency logic and Type A-only retrieval-depth scoring.
2. Add missing unstructured action-item emission.
3. Correct filename timestamp format and add regression tests.
4. Remove low-severity dead/duplicated code and keep tests green.
