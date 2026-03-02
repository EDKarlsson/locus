# Write Modes

Locus has two distinct write modes. Using the wrong one for a given situation
is the most common source of palace degradation.

## Canonical Files

**What they are:** Authoritative, durable facts that persist across sessions.
The source of truth for a room.

**Examples:** A room's main file, a `platform-services.md` inventory,
a `technical-gotchas.md` knowledge base.

**Rules:**
- Explicitly edited — never appended to blindly
- Content is verified before writing (don't record assumptions as facts)
- Old content is removed or superseded when updated, not left alongside
- Git diff should be meaningful: a reader can understand what changed and why
- One agent edits at a time (last-write-wins; git history is the audit trail)

**When to write:**
- A fact has been confirmed as durable (survives beyond the current session)
- An existing entry is wrong or outdated and needs correction
- A new topic warrants a permanent record

## Session Logs

**What they are:** Ephemeral, append-only records of what happened during
a session. Raw material for future consolidation.

**Location:** `<room>/sessions/YYYY-MM-DD.md`

**Rules:**
- Append-only — never edit a session log after writing
- One file per calendar day per room; create a new file each day
- No size limit — log everything relevant
- Not authoritative — session logs are drafts, not facts

**Format:**

```markdown
# Session YYYY-MM-DD

## Context
<What task was being worked on when this room was accessed.>

## Findings
<What was learned or confirmed during this session.>

## Actions Taken
<What was written, changed, or decided.>

## Consolidation Notes
<Anything that should be promoted to a canonical file on next consolidation.>
```

**When to write:**
- At the end of a session that touched a room
- When something notable happened that may or may not be durable
- When uncertain whether a finding warrants a canonical entry yet

## Decision Guide

```
Is this fact confirmed and durable?
├── Yes → Write to canonical file
└── No  → Is it worth recording for potential future use?
          ├── Yes → Append to session log
          └── No  → Do not write
```

## Common Mistakes

**Appending to canonical files instead of editing them**
Results in duplicate or contradictory information accumulating in the same file.
Canonical files must be edited, not grown.

**Treating session logs as canonical**
Session logs are drafts. Citing them as authoritative causes agents to rely on
unverified, potentially stale information.

**Not writing session logs**
When consolidation runs, it needs raw material to work from. Sessions that
leave no log leave no trail for the palace to learn from.

**Writing to the wrong room**
If a finding applies globally (e.g., a toolchain preference), it belongs in
a global room, not a project room. Misplaced canonical facts are hard to find
and create inconsistency.
