# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

**Locus** is a hierarchical markdown-based memory system for AI agents — each directory is a "room" (locus) in the palace, containing specific knowledge navigated on demand. Keeps context windows small while enabling precise, deep recall. Named for the atomic unit of the Method of Loci.

Must be **agent-agnostic**: usable by Claude, Codex, Gemini, or any LLM-based agent.

## Existing Memory Patterns to Study

Before writing anything new, read these reference implementations:

| Location | What it shows |
|---|---|
| `/home/dank/.claude/projects/-home-dank-git-valhalla-homelab-iac/memory/` | 8-file memory system: MEMORY.md + specialty files |
| `/home/dank/.claude/projects/-home-dank-git-valhalla-agent-control-plane/memory/` | Multi-agent orchestration memory |
| `~/.claude/skills/*/SKILL.md` | Skill definition format (9 skills to study) |
| `~/.claude/commands/` | Command format for reusable workflows |

The homelab-iac memory is the most mature reference (700+ line MEMORY.md, specialty files for gotchas, deployments, platform services).

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

## Skill Format

Skills live in `~/.claude/skills/<skill-name>/SKILL.md`. The existing 9 skills cover:
- Mentorship workflows (`guided-walkthrough`, `guided-iac-walkthrough`)
- Project management (`project-triage`, `review-analyzer`, `knowledge-capture`)
- Infrastructure diagnostics (`homelab-vm-debug`, `homelab-health`, `k8s-mcp-reconnect`)
- Integrations (`op-ssh-agent`, `wikijs-docs-sync`)

The Locus skill should follow this same directory/SKILL.md pattern.

## Cross-Agent Compatibility

Skills and commands are mirrored across agents:
- Claude: `~/.claude/skills/` and `~/.claude/commands/`
- Codex: `.codex/commands/` in project repos
- Gemini: `.gemini/` in project repos + GitHub Actions via `add-gemini-action`

Any skill produced here must be expressible in plain markdown that any agent can follow without Claude-specific tooling.

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

## Related Projects

- `~/git/valhalla/homelab-iac` — primary reference for memory patterns; has `.codex/`, `.gemini/`, `.claude/` configs
- `~/git/valhalla/agent-control-plane` — multi-agent orchestration hub (agent_hub.py, plugin_manager.py); Phase 9 (GitHub plugin system) is in progress
- `~/.claude/projects/-home-dank-git-valhalla-homelab-iac/memory/` — study `technical-gotchas.md` and `worktree-workflow.md` for file format patterns
