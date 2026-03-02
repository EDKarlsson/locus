# INDEX.md Format

The INDEX.md is the palace entry point. Every agent reads this first.
It must answer: "what rooms exist and where are they?" in under 50 lines.

## Schema

```markdown
# <Palace Name>

<One sentence describing the scope of this palace.>

## Global Rooms

Rooms shared across all projects.

| Room | Description | Path |
|---|---|---|
| `<room-name>` | <One-line description> | `global/<room-name>/` |

## Project Rooms

| Room | Description | Path |
|---|---|---|
| `<project-name>` | <One-line description> | `projects/<project-name>/` |

---
_Last consolidated: YYYY-MM-DD_
```

## Field Definitions

**Palace Name** — The name of this Locus instance. For a global palace,
use the owner/system name. For a project palace, use the project name.

**Room name** — kebab-case, matches the directory name exactly.
Do not abbreviate; prefer `technical-gotchas` over `tech-gotchas`.

**Description** — One line, present tense, describes what knowledge lives
in the room. Not what the room is for — what it contains.
- Good: `Proxmox node IPs, K3s versions, and deployed service endpoints`
- Bad: `Infrastructure reference information`

**Path** — Relative path from the palace root to the room directory.
Always ends with `/`.

**Last consolidated** — ISO date of the most recent consolidation run.
Agents use this to judge whether the palace may be stale.

## Navigation Protocol

When entering the palace, an agent must:

1. Read `INDEX.md` (this file).
2. Identify the room(s) relevant to the current task.
3. Read only those rooms — do not load the full palace.
4. If no room matches, check whether a new room is warranted before
   writing to an existing one.

## Sub-Indices

When the palace exceeds the 50-line INDEX.md budget, split into sub-indices:

```
INDEX.md                  ← root index, points to sub-indices
global/
  INDEX.md                ← global rooms index
projects/
  <project-name>/
    INDEX.md              ← project rooms index
```

The root INDEX.md in this case lists sub-index paths, not individual rooms.

## Example

```markdown
# Homelab Palace

Cross-session memory for homelab infrastructure and agent workflows.

## Global Rooms

| Room | Description | Path |
|---|---|---|
| `toolchain` | Preferred tools, versions, and CLI conventions | `global/toolchain/` |
| `agent-patterns` | Recurring agent workflow patterns and gotchas | `global/agent-patterns/` |
| `user-preferences` | Communication style and workflow preferences | `global/user-preferences/` |

## Project Rooms

| Room | Description | Path |
|---|---|---|
| `api-platform` | Service mesh, auth layer, deployment topology, key config | `projects/api-platform/` |
| `data-pipeline` | ETL jobs, schema versions, known failure modes | `projects/data-pipeline/` |
| `mobile-app` | Release status, open bugs, architecture decisions | `projects/mobile-app/` |

---
_Last consolidated: 2026-03-02_
```
