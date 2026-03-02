---
name: locus-consolidate
description: >
  Consolidate a Locus memory palace room. Merges session logs into canonical
  files, supersedes stale entries, archives processed logs, and enforces size
  limits. Use when a room's session directory has more than 5 unprocessed logs,
  the same room has been accessed in 3 or more consecutive sessions, a room
  main file exceeds 150 lines, or the user asks to consolidate or clean up memory.
---

# Locus Consolidate (Gemini)

Merges accumulated session logs into canonical room files, enforces size limits,
and archives processed logs. Run per room.

**Input:** room path relative to palace root, passed via `$ARGUMENTS`,
workflow input, or `LOCUS_ROOM` environment variable.
If omitted, auto-detect rooms needing consolidation.

---

## Step 1 — Identify the target room

**1a — Room path provided:**
Read the room's main file and list `sessions/` contents.
Confirm the room exists and qualifies (>5 unarchived logs or main file >150 lines).

**1b — Auto-detect:**
Read `INDEX.md` to enumerate all rooms. For each room:
- Count files in `sessions/` not in `sessions/archived/`
- Check line count of the room main file

Process qualifying rooms one at a time. In GitHub Actions, log each detected
room as a workflow step summary.

---

## Step 2 — Read the room state

Read:
1. Room main file
2. All unprocessed session logs (files in `sessions/` not in `sessions/archived/`),
   oldest-first (alphabetical order = chronological order)

Do not read specialty files unless explicitly referenced in Consolidation Notes.

---

## Step 3 — Extract consolidation candidates

From each session log, extract `### Consolidation Notes` content.
Build a working list of changes. Newer notes supersede older on the same topic.
Flag irreconcilable conflicts rather than silently resolving them.

---

## Step 4 — Merge into canonical files

For each candidate:
1. Edit the target canonical file explicitly in place.
2. Update facts — do not append alongside old versions.
3. After edits, verify line counts stay within limits:
   - Room main file: ≤ 200 lines
   - Specialty files: ≤ 300 lines
4. If over limit: extract the largest self-contained section to a new
   specialty file and add a one-line reference in the main file.

---

## Step 5 — Archive processed session logs

Move processed logs to `<room>/sessions/archived/`. Create the directory if needed.
Do not delete — archival preserves the audit trail.

Conflicted logs stay in place with this comment prepended:
```
<!-- CONSOLIDATION PENDING: conflicts flagged, requires review -->
```

---

## Step 6 — Update INDEX.md

Check whether the room's description still reflects its contents after merging.
Edit in place if drifted. Verify INDEX.md remains under 50 lines.

---

## Step 7 — Report

```
Locus Consolidate: <room-path>
  Session logs processed:  <N>
  Canonical files updated: <list>
  Specialty files created: <list or none>
  Logs archived:           <N>
  Conflicts flagged:       <N or none>
  Room main file:          <final line count> lines
  INDEX.md updated:        yes/no
```

In GitHub Actions, write this report to `$GITHUB_STEP_SUMMARY`.

## GitHub Actions Usage

```yaml
- uses: google-github-actions/run-gemini-cli@v0
  with:
    prompt_file: skills/gemini/locus-consolidate/SKILL.md
    env: |
      LOCUS_PALACE=${{ inputs.palace_path }}
      LOCUS_ROOM=${{ inputs.room_path }}
```

## Installation

```sh
cp -r skills/gemini/locus-consolidate .gemini/locus-consolidate
```
