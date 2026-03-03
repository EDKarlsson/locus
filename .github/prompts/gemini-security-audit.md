# Gemini Code Assist GitHub Action Prompt: Security Audit + Reporting

You are running in GitHub Actions. Execute a full security audit pass and generate auditable artifacts.

## Workflow

1. Install dependencies:
   - `uv sync --extra dev`
2. Run unit tests:
   - `uv run pytest tests/unit/ -v --tb=short`
3. Run security tooling:
   - `mkdir -p docs/audits/artifacts`
   - `uv run --with bandit bandit -r locus -f json -o docs/audits/artifacts/gemini-bandit.json || true`
   - `uv run --with pip-audit pip-audit > docs/audits/artifacts/gemini-pip-audit.txt 2>&1 || true`
4. Manually review exploitability and attack vectors in:
   - `locus/mcp/`
   - `locus/agent/`
   - `.github/workflows/`
   - dependency configuration (`pyproject.toml`, `uv.lock`)

## Deliverables

Write:

1. `docs/audits/gemini-security-pr-review-report.md`
2. `docs/audits/gemini-security-pr-comment.md`

## Full Report Schema

1. Executive summary
2. Scope and methodology
3. Scanner results summary
4. Findings by severity
5. For each finding:
   - ID
   - Severity
   - Location with line numbers
   - Evidence
   - Exploit narrative
   - Impact
   - Fix recommendation
   - Temporary mitigation
6. Final merge recommendation

## Output Discipline

- Be explicit about uncertainty.
- Do not overstate scanner output.
- If no major issues are found, still include residual risks and hardening suggestions.
