# AI Security Audit Prompts for GitHub Actions

These prompts are intended to run security tests, auditing, and reporting in PR workflows.

## Prompt Paths

- Claude: `.github/prompts/claude-security-audit.md`
- Codex: `.github/prompts/codex-security-audit.md`
- Copilot: `.github/prompts/copilot-security-audit.md`
- Gemini: `.github/prompts/gemini-security-audit.md`

## Added Workflow Files

- Claude audit workflow: `.github/workflows/claude-security-audit.yml`
- Copilot setup workflow: `.github/workflows/copilot-setup-steps.yml`
- PR auto-comment workflow: `.github/workflows/post-ai-security-pr-comment.yml`

## Generic Workflow Pattern

```yaml
name: AI Security Audit

on:
  pull_request:
  workflow_dispatch:

jobs:
  security-audit:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - name: Run AI security review
        uses: <provider-action>
        with:
          prompt_file: .github/prompts/codex-security-audit.md
```

Replace `<provider-action>` with your configured runner for Claude, Codex, Copilot, or Gemini.

## Claude Example

This repo now includes a runnable Claude workflow:

```yaml
.github/workflows/claude-security-audit.yml
```

It reads `.github/prompts/claude-security-audit.md`, runs Claude via the
Anthropic GitHub Action, and uploads audit artifacts from `docs/audits/`.

## Automatic PR Comment Posting

This repo now includes a follow-up workflow:

```yaml
.github/workflows/post-ai-security-pr-comment.yml
```

It triggers after `Claude Security Audit` completes successfully on a PR,
downloads the `claude-security-audit` artifact, and posts
`*-security-pr-comment.md` to the PR automatically.

## Copilot Example

This repo now includes the official Copilot coding-agent setup workflow:

```yaml
.github/workflows/copilot-setup-steps.yml
```

Use it with the Copilot prompt file:

```text
.github/prompts/copilot-security-audit.md
```

## Gemini Example

Gemini already has a documented action pattern in this repo:

```yaml
- uses: google-github-actions/run-gemini-cli@v0
  with:
    prompt_file: .github/prompts/gemini-security-audit.md
```

## Recommended Follow-up Steps

After the AI step, add normal artifact and PR-comment publishing steps, for example:

1. Upload `docs/audits/artifacts/*` as workflow artifacts.
2. Post `docs/audits/*-security-pr-comment.md` to the PR.
3. Fail the workflow if the comment/report says `Request changes`.
