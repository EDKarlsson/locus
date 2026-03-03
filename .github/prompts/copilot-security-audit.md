# Copilot GitHub Action Prompt: Security Audit + Reporting

Run a security review of this repository inside GitHub Actions and produce a clear PR recommendation with artifacts.

## Mandatory Steps

1. Install dependencies:
   - `uv sync --extra dev`
2. Run tests:
   - `uv run pytest tests/unit/ -v --tb=short`
3. Run security checks:
   - `mkdir -p docs/audits/artifacts`
   - `uv run --with bandit bandit -r locus -f json -o docs/audits/artifacts/copilot-bandit.json || true`
   - `uv run --with pip-audit pip-audit > docs/audits/artifacts/copilot-pip-audit.txt 2>&1 || true`
4. Perform manual code review for vulnerabilities in:
   - `locus/mcp/server.py`
   - `locus/mcp/palace.py`
   - `locus/agent/config.py`
   - `.github/workflows/*.yml`

## Output Files

1. Full report:
   - `docs/audits/copilot-security-pr-review-report.md`
2. Short review comment:
   - `docs/audits/copilot-security-pr-comment.md`

## Findings Requirements

For every finding include:

- Severity (`Critical` / `High` / `Medium` / `Low`)
- Exact location (file + line)
- Evidence
- Attack vector
- User/business impact
- Recommended remediation

## Decision

End with one of:

- `Approve`
- `Request changes`

Use `Request changes` when any unresolved `High` or `Critical` issue is present.
