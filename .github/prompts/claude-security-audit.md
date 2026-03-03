# Claude GitHub Action Prompt: Security Audit + Reporting

You are running in GitHub Actions on this repository. Perform a security-focused audit and produce actionable artifacts.

## Objectives

1. Run security-relevant tests and scans.
2. Identify vulnerabilities, attack vectors, and exploitability.
3. Produce a full markdown report and a short PR-ready summary comment.

## Required Execution Plan

1. Install dependencies:
   - `uv sync --extra dev`
2. Run baseline tests:
   - `uv run pytest tests/unit/ -v --tb=short`
3. Run security scanners and save artifacts:
   - `mkdir -p docs/audits/artifacts`
   - `uv run --with bandit bandit -r locus -f json -o docs/audits/artifacts/claude-bandit.json || true`
   - `uv run --with pip-audit pip-audit > docs/audits/artifacts/claude-pip-audit.txt || true`
4. Perform targeted manual review of:
   - `locus/mcp/*.py`
   - `locus/agent/*.py`
   - `.github/workflows/*.yml`
   - `pyproject.toml`

## Report Requirements

Write a full report to:

- `docs/audits/claude-security-pr-review-report.md`

Report sections must include:

1. Executive summary
2. Scope and methods
3. Findings ordered by severity
4. For each finding:
   - Rule ID
   - Severity (`Critical`/`High`/`Medium`/`Low`)
   - Location (file + line)
   - Evidence
   - Impact
   - Exploit scenario
   - Recommended fix
   - Mitigation if fix cannot land now
5. Scanner outputs summary
6. Merge recommendation (`approve` or `request changes`)

## PR Comment Output

Also write a concise comment draft to:

- `docs/audits/claude-security-pr-comment.md`

The comment must include:

1. Top blocking findings (if any)
2. Commands executed
3. Artifact paths
4. Clear merge recommendation

## Quality Bar

- Do not claim vulnerabilities without concrete evidence.
- Use exact file paths and line numbers.
- If no significant issues are found, explicitly say so and list residual risks.
- Prefer practical fixes with minimal regression risk.
