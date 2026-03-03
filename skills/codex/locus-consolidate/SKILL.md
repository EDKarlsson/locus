---
name: locus-consolidate
description: >
  Consolidate a Locus memory palace room. Merges session logs into canonical
  files, supersedes stale entries, archives processed logs, and enforces size
  limits. Use when a room's session directory has more than 5 unprocessed logs,
  the same room has been accessed in 3 or more consecutive sessions, a room
  main file exceeds 150 lines, or the user asks to consolidate or clean up memory.
---

# Locus Consolidate (Codex)

Merges accumulated session logs into canonical room files, enforces size limits,
and archives processed logs. Run per room.

**Arguments:** room path relative to palace root (e.g. `projects/my-project`).
If omitted, auto-detect rooms needing consolidation (Step 1b).

---

## Step 1 — Identify the target room

**1a — Argument provided:**
```sh
ls <palace-root>/<room-path>/sessions/
wc -l <palace-root>/<room-path>/<room-name>.md
```
Verify the room exists and has session logs or exceeds size limits.

**1b — No argument (auto-detect):**
```sh
# Find session dirs with unarchived logs
find <palace-root> -path "*/sessions/*.md" ! -path "*/archived/*" | sort

# Find room main files over 150 lines
find <palace-root> -name "*.md" ! -path "*/sessions/*" | xargs wc -l | awk '$1 > 150'
```
Process qualifying rooms one at a time.

---

## Step 2 — Read the room state

```sh
cat <room>/<room-name>.md
ls <room>/sessions/          # list all logs
ls <room>/sessions/archived/ # list already processed (if dir exists)

# Read unprocessed logs oldest-first
for f in $(ls <room>/sessions/*.md | sort); do cat "$f"; done
```

---

## Step 3 — Extract consolidation candidates

From each session log, collect `### Consolidation Notes` content.
Build a working list of changes to apply. Newer notes supersede older ones
on the same topic. Flag irreconcilable conflicts for review.

---

## Step 4 — Merge into canonical files

For each candidate:
1. Edit the target canonical file in place (targeted patch, not append).
2. After all edits, check line counts:
   ```sh
   wc -l <canonical-file>
   ```
3. If over the limit (200 for main files, 300 for specialty files):
   - Extract the largest self-contained section to a new specialty file.
   - Replace with a one-line reference in the main file.

---

## Step 5 — Archive processed session logs

```sh
mkdir -p <room>/sessions/archived
mv <room>/sessions/YYYY-MM-DD.md <room>/sessions/archived/
```

Leave conflicted logs in place with a comment at the top:
```
<!-- CONSOLIDATION PENDING: conflicts flagged, requires review -->
```

---

## Step 6 — Update INDEX.md

Check whether the room's description in `INDEX.md` still reflects its contents.
Edit in place if it has drifted. Verify `INDEX.md` remains under 50 lines:
```sh
wc -l <palace-root>/INDEX.md
```

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

## Installation

```sh
cp -r skills/codex/locus-consolidate ~/.codex/skills/locus-consolidate
```
