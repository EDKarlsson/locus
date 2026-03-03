# AI Security Audit Prompts for GitHub Actions

These prompts are intended to run security tests, auditing, and reporting in PR workflows.

## Prompt Paths

- Claude: `.github/prompts/claude-security-audit.md`
- Codex: `.github/prompts/codex-security-audit.md`
- Copilot: `.github/prompts/copilot-security-audit.md`
- Gemini: `.github/prompts/gemini-security-audit.md`

## Added Workflow Files

- Claude audit workflow (manual-only): `.github/workflows/claude-security-audit.yml`
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
      contents: read        # read-only; only elevate to write if the action must commit
      pull-requests: write  # needed to post review comments
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
      - name: Run AI security review
        uses: <provider-action>
        with:
          prompt_file: .github/prompts/codex-security-audit.md
```

> **Supply-chain note:** Third-party actions are pinned to mutable tags above for
> readability. For production pipelines, pin to immutable commit SHAs and use a
> tool like Renovate or Dependabot to keep them updated.

Replace `<provider-action>` with your configured runner for Claude, Codex, Copilot, or Gemini.

## Claude Example

This repo now includes a Claude workflow configured as manual-only
(`workflow_dispatch`) so it is disabled for automatic PR runs:

```yaml
.github/workflows/claude-security-audit.yml
```

It reads `.github/prompts/claude-security-audit.md`, runs Claude via the
Anthropic GitHub Action, and uploads audit artifacts from `docs/audits/`.
To trigger the audit for a specific PR and have the comment auto-posted, supply
the `pr_number` dispatch input when running the workflow manually.

## Automatic PR Comment Posting

This repo now includes a follow-up workflow:

```yaml
.github/workflows/post-ai-security-pr-comment.yml
```

It triggers after `Claude Security Audit` completes successfully when a
`pr_number` input was provided at dispatch time, downloads the
`claude-security-audit` artifact, and posts `*-security-pr-comment.md` to
the specified PR automatically.

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

> **Supply-chain note:** Pin `google-github-actions/run-gemini-cli` to a
> commit SHA in production to guard against upstream tag changes.

## Recommended Follow-up Steps

After the AI step, add normal artifact and PR-comment publishing steps, for example:

1. Upload `docs/audits/artifacts/*` as workflow artifacts.
2. Post `docs/audits/*-security-pr-comment.md` to the PR.
3. Fail the workflow if the comment/report says `Request changes`.
