# Security Audit Prompt Pack (GitHub Actions)

Prompt files in this directory are designed for AI-assisted GitHub Actions jobs that run security tests, vulnerability auditing, and PR reporting.

## Prompt Files

- `claude-security-audit.md`
- `codex-security-audit.md`
- `copilot-security-audit.md`
- `gemini-security-audit.md`

## Expected Artifacts

Each prompt directs the agent to generate:

1. A full report in `docs/audits/`
2. Scanner artifacts in `docs/audits/artifacts/`
3. A short PR comment draft in `docs/audits/`

## GitHub Actions Wiring

Use your provider action with `prompt_file` set to one of these files.

Example step shape:

```yaml
- name: Security Audit (AI)
  uses: <provider-action>
  with:
    prompt_file: .github/prompts/codex-security-audit.md
```

Replace `<provider-action>` with your configured Claude/Codex/Copilot/Gemini Action runner.

## Included Workflows

- Claude runnable workflow: `.github/workflows/claude-security-audit.yml`
- Copilot coding-agent setup workflow: `.github/workflows/copilot-setup-steps.yml`
- Auto-comment workflow: `.github/workflows/post-ai-security-pr-comment.yml`
