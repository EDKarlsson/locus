# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

**Locus** is a hierarchical markdown-based memory system for AI agents — each directory is a "room" (locus) in the palace, containing specific knowledge navigated on demand. Keeps context windows small while enabling precise, deep recall. Named for the atomic unit of the Method of Loci.

Must be **agent-agnostic**: usable by Claude, Codex, Gemini, or any LLM-based agent.

## Existing Memory Patterns to Study

Before writing anything new, read these reference implementations:

| Location | What it shows |
|---|---|
| `~/.claude/projects/<project>/memory/` | 8-file memory system: MEMORY.md + specialty files |
| `~/.claude/projects/<project>/memory/` | Multi-agent orchestration memory |
| `~/.claude/skills/*/SKILL.md` | Skill definition format (9 skills to study) |
| `~/.claude/commands/` | Command format for reusable workflows |

A mature memory directory typically has a ~200-line MEMORY.md plus specialty files for gotchas, deployments, and platform services.

## Memory File Conventions (from existing projects)

**Structure of MEMORY.md:**
1. Project overview (1–3 sentences + key stats)
2. Architecture/topology
3. Configuration sections by subsystem
4. Key file paths
5. Current phase/status
6. References to specialty files

**Specialty file patterns:**
- `technical-gotchas.md` — header-per-issue, symptom → root cause → resolution
- `platform-services.md` — quick-reference table (service → version → IP/config)
- `deployment-issues.md` — numbered issues with detailed logging

**Context window discipline:** MEMORY.md is always loaded (~200 line limit enforced by auto-memory system). Specialty files are read on demand. This is the core design constraint the skill must encode.

## Runtime Architecture

Locus has two complementary interfaces:

**1. SKILL.md files** — the primary interface. Skills live in `~/.claude/skills/<name>/SKILL.md`
and are compatible with both Claude Code CLI and the Claude Agent SDK
(`settingSources: ["user", "project"]`). The existing 9 skills are references:
`guided-walkthrough`, `project-triage`, `knowledge-capture`, etc.

**2. Agent SDK entrypoint** (`locus/agent/`) — a Python application using
`claude_agent_sdk` that runs Locus autonomously against a palace directory.
Used for benchmarking, integration testing, and as the foundation for the
v0.5 MCP server.

```python
# SDK configuration pattern
ClaudeAgentOptions(
    cwd=palace_path,
    setting_sources=["user", "project"],  # loads SKILL.md files
    allowed_tools=["Skill", "Read", "Write", "Bash"],
)
```

**Critical:** `allowed-tools` frontmatter in SKILL.md is only honoured by Claude Code CLI,
not the Agent SDK. Never rely on it — control tool access via the host `allowedTools` config.

## Cross-Agent Compatibility

Skills mirror across agents:
- Claude: `~/.claude/skills/` · Agent SDK: `settingSources: ["user", "project"]`
- Codex: `.codex/commands/` in project repos
- Gemini: `.gemini/` in project repos + GitHub Actions via `add-gemini-action`

SKILL.md files must work without `allowed-tools` frontmatter to remain SDK-compatible.

## Development Process (from SPECIFICATION.md)

1. **Analysis phase** — full project analysis + generate clarifying questions
2. **Project plan** — export to GitHub, GitLab, or YouTrack (best judgement call)
3. **Phase breakdown** — map tasks to the project plan interface
4. **Multi-agent review** — code reviewed by multiple agents covering:
   - Unit tests + code coverage
   - Architecture analysis
   - Security analysis and testing
   - Integration testing
5. **Local agent leverage** — use Gemini, Codex, and Claude in parallel

## Related Resources

- `~/.claude/projects/<project>/memory/` — study any mature memory directory for `technical-gotchas.md` and `worktree-workflow.md` file format patterns
- The `example-palace/` directory in this repo is the canonical reference for palace structure
