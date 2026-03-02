# Locus — Agent Onboarding Guide

Locus is a hierarchical markdown memory system. Directories are rooms, files
are knowledge. Agents navigate it on demand — only loading what they need.

---

## 1. Install

**Claude:**
```sh
cp -r skills/claude/locus ~/.claude/skills/locus
cp -r skills/claude/locus-consolidate ~/.claude/skills/locus-consolidate
```

**Codex:**
```sh
cp -r skills/codex/locus ~/.codex/skills/locus
cp -r skills/codex/locus-consolidate ~/.codex/skills/locus-consolidate
```

**Gemini:** Place `skills/gemini/locus/SKILL.md` in your project's `.gemini/`
directory, or reference it directly in a GitHub Actions workflow.

**Agent SDK (Python):**
```sh
pip install -e .
# or: uv pip install -e .
```

---

## 2. Create a palace

Copy the INDEX.md template and create your first room:

```sh
# Create palace root
mkdir -p ~/.locus/global/toolchain/sessions
mkdir -p ~/.locus/projects/my-project/sessions

# Copy templates
cp templates/INDEX.md ~/.locus/INDEX.md
cp templates/room/room-name.md ~/.locus/global/toolchain/toolchain.md
cp templates/room/sessions/YYYY-MM-DD.md ~/.locus/global/toolchain/sessions/
```

Edit `~/.locus/INDEX.md` — fill in your palace name and room entries.
Keep it under 50 lines. This is the only file loaded automatically.

**Palace locations (checked in order):**
1. Path passed as argument
2. `.locus/` in the current project
3. `~/.locus/` global palace

---

## 3. Starting a session

The `locus` skill handles this automatically when invoked. Manually:

1. Read `INDEX.md` — identify relevant rooms
2. Read only those rooms' main files
3. Read specialty files only if directly relevant
4. Never load the full palace speculatively

**Context budget:** INDEX.md ≤ 50 lines. Room main files ≤ 200 lines.
If a room is too large, that's a consolidation signal.

---

## 4. Writing memories

**Durable fact (survives across sessions):**
Edit the canonical file explicitly. Update in place — never append alongside
old content. Stay within the 200-line room limit.

**Session finding (may or may not be durable):**
Append to `<room>/sessions/YYYY-MM-DD.md`. Never edit after writing.
Use the session log template — the `### Consolidation Notes` section is
what `locus-consolidate` reads when processing logs.

**Decision guide:**
```
Is this confirmed and durable?  →  Yes: edit canonical file
                                →  No:  append to session log
```

---

## 5. Ending a session

Before closing, write a session log for every room you touched:

```
<room>/sessions/YYYY-MM-DD.md
```

Fill in Findings, Actions Taken, and — critically — Consolidation Notes.
Specific notes ("promote K3s API IP to Overview section") are far more
useful than vague ones ("update the room").

---

## 6. Consolidation

Run `locus-consolidate` (or invoke the skill) when:

| Trigger | Threshold |
|---|---|
| Unprocessed session logs | > 5 in `sessions/` |
| Consecutive sessions touching a room | ≥ 3 |
| Room main file size | > 150 lines (soft), > 200 lines (must act) |
| INDEX.md size | > 40 lines |

Consolidation merges session logs → canonical files, archives processed logs,
and enforces size limits. Conflicts are flagged, not silently resolved.

---

## 7. Agent SDK entrypoint

Run Locus autonomously against any palace:

```sh
# Basic query
locus --palace ~/.locus --task "What toolchain conventions are set?"

# With metrics output for benchmarking
locus --palace ~/.locus \
      --task "What K3s gotchas exist?" \
      --metrics-file tests/results/2026-03-02.json

# JSON output (for scripting)
locus --palace ~/.locus --task "..." --json
```

The agent loads the `locus` skill automatically via `setting_sources`.
Metrics track retrieval depth and context size per run.

---

## 8. Quick reference

| Action | Skill | Command |
|---|---|---|
| Navigate palace | `locus` | Invoke skill or `locus --palace ... --task ...` |
| Write session log | `locus` (Step 4) | Append to `sessions/YYYY-MM-DD.md` |
| Consolidate a room | `locus-consolidate` | Invoke with room path |
| Auto-detect + consolidate | `locus-consolidate` | Invoke with no argument |

**Spec reference:** `spec/` directory contains the full convention definitions.
Read `spec/size-limits.md` first if you're unsure about any threshold.
