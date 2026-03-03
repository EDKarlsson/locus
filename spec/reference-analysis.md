# Reference Analysis

Patterns extracted from a mature infrastructure memory system — one of the earliest
implementations. These inform Locus conventions.

## Infrastructure Project Memory System

**Location:** `~/.claude/projects/<project-hash>/memory/`

### File Inventory

| File | Role | Structure |
|---|---|---|
| `MEMORY.md` | Always-loaded entry point | Overview → Architecture → Config → Key Files → Phase/Status → References |
| `platform-services.md` | Quick-reference lookup | Table: service → version → IP/config |
| `technical-gotchas.md` | Failure knowledge | Header-per-issue: symptom → root cause → resolution |
| `deployment-issues.md` | Incident log | Numbered issues with detailed logging |
| `1password-research.md` | Verified research | Findings vs official docs |
| `tailscale-kubernetes.md` | Integration patterns | Narrative with config snippets |
| `nexus-migration.md` | Procedures | Step-by-step with confirmed gotchas |
| `workstations.md` | Hardware reference | Config details per node |

### Observed Patterns

**Entry point discipline**
- `MEMORY.md` is always loaded into context; specialty files are read on demand.
- The auto-memory system truncates `MEMORY.md` at ~200 lines — anything beyond is invisible.
- This makes the 200-line limit a hard constraint, not a preference.

**Specialty file naming**
- Names are descriptive nouns tied to the domain: `technical-gotchas`, `platform-services`, `nexus-migration`.
- Not generic names like `notes` or `misc`.
- One topic per file — a reader can predict the file's contents from its name alone.

**Specialty file structure**
- Each file has a consistent internal structure for its role (tables for lookups, headers-per-issue for gotchas, numbered steps for procedures).
- Structure is chosen to minimise scanning — readers find the relevant section quickly.

**What's missing (gaps Locus should fill)**
- No `INDEX.md` — agents must infer the palace layout from `MEMORY.md`'s References section.
- No session logs — all writes go directly to canonical files, creating noise in git history.
- No explicit size threshold enforcement — `MEMORY.md` grew to 700+ lines before truncation became a problem.
- No consolidation mechanism — stale entries accumulate.

## Multi-Agent Orchestration Memory System

**Location:** `~/.claude/projects/<project-hash>/memory/`

Focuses on multi-agent orchestration state. Key observation: tracks phase completion
(Phases 1–8 done, Phase 9 in progress) and maps open GitHub issues to phases.
This session-resume pattern is one Locus should formalise as a convention.

## Existing Skill Format

Skills in `~/.claude/skills/<name>/SKILL.md` follow an implicit structure:
1. Skill name + one-line purpose
2. When to invoke
3. Step-by-step instructions (numbered or headed sections)
4. `$ARGUMENTS` placeholder for parameterisation

Nine skills exist covering: mentorship, project management, diagnostics, integrations.
Locus should produce skills that follow this same pattern.

## Key Takeaways for Locus

1. The 200-line always-loaded file limit is the central constraint — design around it.
2. A navigable index (not embedded in the entry file) solves the layout-discovery problem.
3. Specialty files earn their existence by having a clear role and predictable structure.
4. Session logs and canonical files need to be distinct — mixing them pollutes both.
5. Consolidation is a maintenance task that needs a dedicated trigger, not an afterthought.
