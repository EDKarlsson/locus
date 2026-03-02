# Room Conventions

A room is a directory. Its contents are the knowledge stored at that locus.

## Directory Naming

- kebab-case, all lowercase
- Noun-based — name the domain, not the purpose
  - Good: `technical-gotchas`, `platform-services`, `deployment-issues`
  - Bad: `notes`, `misc`, `temp`, `info`
- Singular preferred for concepts (`toolchain`, not `toolchains`)
- Plural acceptable for collections (`gotchas`, `services`, `issues`)

## Room Structure

Every room contains at minimum one main file and optionally specialty files
and a session log directory:

```
<room-name>/
  <room-name>.md       ← main file (always read when entering the room)
  <specialty>.md       ← optional, topic-specific deep dives
  sessions/            ← optional, append-only session logs
    YYYY-MM-DD.md
```

**Main file** — named after the room (e.g., `toolchain/toolchain.md`).
Alternatively `README.md` for rooms intended to be browsed on GitHub.
Must stay within the 200-line limit. Contains: overview, key facts,
and references to specialty files.

**Specialty files** — named for their content, not their format:
- `technical-gotchas.md` — issues encountered, with symptom/cause/resolution
- `platform-services.md` — service inventory table
- `deployment-issues.md` — incident log
- `migration-procedures.md` — step-by-step operational procedures

**Session log directory** — `sessions/` contains one file per session,
named by date. Append-only. Never edited after writing.

## Nesting

Rooms may be nested up to **3 levels deep**:

```
projects/
  homelab-iac/             ← level 1
    networking/            ← level 2
      tailscale/           ← level 3
        tailscale.md
```

Beyond 3 levels, flatten the structure or merge rooms.

## Internal Structure of Main Files

Main files follow a consistent section order:

```markdown
# <Room Name>

<One paragraph: what this room covers and when to read it.>

## Overview
<Key facts, current state, essential numbers.>

## <Topic Section>
<Domain-specific content.>

## Key Files
<Canonical paths to important files, configs, or code.>

## References
<Links to specialty files in this room, with one-line descriptions.>
```

Not all sections are required. Omit sections that don't apply.
The References section is required if specialty files exist.

## Specialty File Structure

Choose structure based on the file's role:

| Role | Structure |
|---|---|
| Lookup / inventory | Table: item → attributes |
| Failure knowledge | `## <Issue Title>` → **Symptom** / **Cause** / **Resolution** |
| Procedures | Numbered steps, one action per step |
| Research / findings | Assertions with evidence, source links |
| Incident log | Numbered entries, newest last |

## File Naming

- kebab-case, all lowercase
- `.md` extension always
- No date prefixes on canonical files (dates belong in session logs)
- Session logs: `sessions/YYYY-MM-DD.md`
  - If multiple sessions occur on the same day: `sessions/YYYY-MM-DD-2.md`
