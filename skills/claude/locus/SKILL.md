---
name: locus
description: >
  Locus memory palace navigation and management. Use when you need to read from
  or write to the agent's memory palace: querying what is known about a topic,
  recording findings from the current session, updating canonical facts,
  navigating to a specific room, or checking whether consolidation is needed.
  Also use at the end of any session that produced new knowledge worth retaining.
---

# Locus — Memory Palace Navigation

Locus is a hierarchical markdown-based memory system. Directories are rooms,
files are knowledge. The goal is always: minimal context loaded, maximum
precision retrieved.

**Compatibility note:** Do not rely on `allowed-tools` frontmatter — use the
tools available in the current environment.

---

## Step 1 — Enter the palace

Always start here, regardless of the task.

1. Locate the palace root. Check in order:
   - `$ARGUMENTS` (if a path was passed to this skill)
   - The project's `.locus/` directory
   - `~/.locus/` for the global palace
2. Read `INDEX.md` from the palace root.
3. Identify the rooms relevant to the current task from the index tables.
   - If no room matches → proceed to Step 5 (new room).
   - If one or more rooms match → proceed to Step 2.

Do not read any other files yet.

---

## Step 2 — Navigate to a room

For each relevant room identified in the index:

1. Read the room's main file (`<room-name>/<room-name>.md` or `README.md`).
2. Check the References section — read specialty files only if they are
   directly relevant to the task.
3. Stop reading when you have enough information. Do not speculatively load files.

Report (internally, not to the user unless asked):
- Which files were read
- Total lines loaded

---

## Step 3 — Write: canonical fact

Use this when recording a durable, verified fact that should persist across sessions.

1. Identify the canonical file that owns this fact (room main file or a specialty file).
2. Read the file if not already loaded.
3. Edit the file explicitly:
   - Update the relevant section in place.
   - Remove or supersede outdated entries — do not append alongside them.
   - Keep the file within its size limit (200 lines for room main files).
4. If the edit would push the file over its limit → extract the growing section
   into a specialty file and add a reference in the main file.
5. Check that `INDEX.md` still accurately describes this room. Update if needed.

---

## Step 4 — Write: session log

Use this for ephemeral findings, unverified information, or anything that may
not be durable. Always write a session log at the end of any session that
touched a room.

1. Determine the target room.
2. Open (or create) `<room-name>/sessions/YYYY-MM-DD.md` using today's date.
   If the file already exists, append to it. If multiple sessions occur on the
   same day, use `YYYY-MM-DD-2.md`, etc.
3. Append using this structure:

```markdown
## <HH:MM> — <brief task description>

### Findings
<Specific facts learned. Avoid vague entries — "checked networking" has no value.>

### Actions Taken
<What was written or changed, with file references.>

### Consolidation Notes
<What should be promoted to a canonical file. Be explicit: "promote X to
Overview section of <room>.md". Leave blank if nothing warrants promotion.>
```

4. Never edit a session log entry after writing it.

---

## Step 5 — Create a new room

Only when no existing room fits the information to be stored.

1. Confirm with the user (or proceed if operating autonomously with clear scope).
2. Create the directory: `<palace-root>/<layer>/<room-name>/`
   - `global/` for cross-project knowledge
   - `projects/<project-name>/` for project-specific knowledge
3. Copy `templates/room/room-name.md` to `<room-name>/<room-name>.md` and fill in.
4. Add the room to `INDEX.md` with a one-line description and its path.
5. Verify `INDEX.md` remains under 50 lines.

---

## Step 6 — Check consolidation triggers

After any write operation, check whether consolidation is needed:

| Condition | Action |
|---|---|
| Room main file > 150 lines (soft limit) | Extract a section into a specialty file |
| Room main file > 200 lines (hard limit) | Must extract before any further writes |
| `sessions/` has > 5 unprocessed logs | Invoke `locus-consolidate` skill |
| Same room accessed 3+ consecutive sessions | Invoke `locus-consolidate` skill |
| INDEX.md > 40 lines | Consider splitting into sub-indices |

---

---

## Step 7 — Inferred feedback (experimental)

After giving a Locus-sourced answer, check whether the user's **immediate
follow-up message** contains a disagreement signal. Only check the next
message — do not scan earlier context.

**Skip inference if:**
- The follow-up is longer than 300 characters (likely a new task)
- It contains a URL, code block, or file path
- The most recent `_metrics/*.json` already has a non-null `feedback` field

**Signal classification:**

| User says | Infer | Examples |
|---|---|---|
| Strong disagreement | `fail` | "that's wrong", "incorrect", "no, that's not right" |
| Mild correction | `partial` | "actually…", "not quite", "you missed…", "try again" |
| Anything else | (no action) | — |

If a signal is detected, record feedback automatically using the same logic
as `/locus-feedback`, with note: `inferred (confidence: <N>) — "<message>"`.

Do not announce that you are recording inferred feedback unless the user asks.
Explicit `/locus-feedback` commands always overwrite inferred entries.

---

## Output

At the end of every Locus operation, emit a brief summary:

```
Locus: read <N> files (<M> lines). Wrote to <file(s)>. [Consolidation needed: yes/no]
```

This summary is used by the Agent SDK metrics collector and the benchmark runner.
