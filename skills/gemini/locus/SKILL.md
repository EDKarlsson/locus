---
name: locus
description: >
  Locus memory palace navigation and management. Use when you need to read from
  or write to the agent's memory palace: querying what is known about a topic,
  recording findings from the current session, updating canonical facts,
  navigating to a specific room, or checking whether consolidation is needed.
  Also use at the end of any session that produced new knowledge worth retaining.
---

# Locus — Memory Palace Navigation (Gemini)

Locus is a hierarchical markdown-based memory system. Directories are rooms,
files are knowledge. The goal is always: minimal context loaded, maximum
precision retrieved.

---

## Step 1 — Enter the palace

Always start here, regardless of the task.

1. Locate the palace root. Check in order:
   - Any path passed as an argument
   - The project's `.locus/` directory
   - `~/.locus/` for the global palace
2. Read `INDEX.md` from the palace root.
3. Identify rooms relevant to the current task from the index tables.
   - If no room matches → proceed to Step 5 (new room).
   - If one or more rooms match → proceed to Step 2.

Do not read any other files yet. If running as a GitHub Actions workflow,
set the palace root via the `LOCUS_PALACE` environment variable or workflow input.

---

## Step 2 — Navigate to a room

For each relevant room:

1. Read the room's main file (`<room-name>/<room-name>.md` or `README.md`).
2. Check the References section — read specialty files only if directly relevant.
3. Stop reading when you have enough information.

Report (internally):
- Which files were read
- Total lines loaded

---

## Step 3 — Write: canonical fact

Use when recording a durable, verified fact that persists across sessions.

1. Identify the canonical file that owns this fact.
2. Read the file if not already loaded.
3. Edit the file explicitly:
   - Update the relevant section in place.
   - Remove or supersede outdated entries.
   - Stay within the 200-line limit for room main files.
4. If the edit would exceed the limit → extract the growing section into a
   specialty file and add a reference in the main file.
5. Verify `INDEX.md` still accurately describes the room. Update if needed.

---

## Step 4 — Write: session log

Use for ephemeral findings or anything not yet confirmed as durable.
Always write a session log at the end of any session that touched a room.

1. Determine the target room.
2. Open or create `<room-name>/sessions/YYYY-MM-DD.md` (today's date).
   If the file exists, append. Multiple sessions same day: `YYYY-MM-DD-2.md`.
3. Append using this structure:

```markdown
## <HH:MM> — <brief task description>

### Findings
<Specific facts learned.>

### Actions Taken
<What was written or changed, with file references.>

### Consolidation Notes
<What to promote to a canonical file. Be explicit. Leave blank if nothing.>
```

4. Never edit a session log entry after writing it.

---

## Step 5 — Create a new room

Only when no existing room fits the information to be stored.

1. Create the room directory and sessions subdirectory.
2. Copy and fill in the room template from `templates/room/room-name.md`.
3. Add the room to `INDEX.md` with a one-line description and path.
4. Verify `INDEX.md` remains under 50 lines.

---

## Step 6 — Check consolidation triggers

After any write, check:

| Condition | Action |
|---|---|
| Room main file > 150 lines | Extract a section into a specialty file |
| Room main file > 200 lines | Must extract before further writes |
| `sessions/` has > 5 unprocessed logs | Run locus-consolidate |
| Same room accessed 3+ consecutive sessions | Run locus-consolidate |
| INDEX.md > 40 lines | Consider splitting into sub-indices |

---

## Output

At the end of every Locus operation, emit:

```
Locus: read <N> files (<M> lines). Wrote to <file(s)>. [Consolidation needed: yes/no]
```

## GitHub Actions Usage

When Locus runs as a Gemini GitHub Actions workflow, use the
`google-github-actions/run-gemini-cli` action with this skill as the prompt:

```yaml
- uses: google-github-actions/run-gemini-cli@v0
  with:
    prompt_file: skills/gemini/locus/SKILL.md
    env: |
      LOCUS_PALACE=${{ inputs.palace_path }}
```

## Installation

For local Gemini CLI use, place in your project's `.gemini/` directory:
```sh
cp skills/gemini/locus/SKILL.md .gemini/locus-skill.md
```
