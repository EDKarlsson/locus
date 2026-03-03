# Codex GitHub Action Prompt: Security Audit + Reporting

You are running in GitHub Actions. Execute a security-focused review of this repository and generate merge-ready reporting artifacts.

## Runbook

1. Install project dependencies:
   - `uv sync --extra dev`
2. Run baseline test coverage:
   - `uv run pytest tests/unit/ -v --tb=short`
3. Run security scanners and capture outputs:
   - `mkdir -p docs/audits/artifacts`
   - `uv run --with bandit bandit -r locus -f json -o docs/audits/artifacts/codex-bandit.json || true`
   - `uv run --with pip-audit pip-audit > docs/audits/artifacts/codex-pip-audit.txt || true`
4. Manually audit attack surfaces in:
   - `locus/mcp/`
   - `locus/agent/`
   - `locus/audit/`
   - `.github/workflows/`
   - `pyproject.toml`

## Deliverables

1. Full report:
   - `docs/audits/codex-security-pr-review-report.md`
2. PR comment draft:
   - `docs/audits/codex-security-pr-comment.md`

## Report Format

Include:

1. Executive summary
2. Scope and commands executed
3. Findings ordered by severity
4. For each finding:
   - ID
   - Severity
   - File and line references
   - Evidence snippet
   - Exploit path / attack vector
   - Impact
   - Recommended fix
   - Short-term mitigation
5. Scanner summary
6. Merge recommendation

## Rules

- Do not report speculative issues without evidence.
- Prefer concrete, low-regression fixes.
- If no blocking issues exist, explicitly state that and list residual risks.
