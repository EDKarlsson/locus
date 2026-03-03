# Palace Audit Algorithm

Defines how `locus-audit` evaluates palace health. The algorithm is
intentionally observable — every score and recommendation traces back
to a specific, readable signal in the palace files.

---

## Inputs

The audit reads three sources:

1. **Palace files** — room sizes, session log counts, directory structure
2. **`_metrics/*.json`** — retrieval depth and lines-loaded per run (from v0.3)
3. **Feedback annotations** — `feedback.quality` values written by `locus-feedback`

All inputs are optional. The audit degrades gracefully: if `_metrics/` is
empty the algorithm skips retrieval-based checks and notes the gap.

---

## Room Discovery

Walk the palace from the root. A **room** is any directory containing a
`<room-name>.md` main file matching its directory name.

```
projects/api-platform/api-platform.md   ← room: api-platform
global/toolchain/toolchain.md           ← room: toolchain
```

Directories without a matching main file are noted as **unstructured** and
flagged separately (not scored).

---

## Per-Room Signals

For each discovered room, collect:

| Signal | How measured |
|---|---|
| `main_lines` | Line count of the room's main `.md` file |
| `specialty_files` | Count of `.md` files in the room dir (excluding main and sessions/) |
| `max_specialty_lines` | Largest specialty file line count |
| `session_log_count` | Count of `.md` files in `sessions/` (excluding `archived/`) |
| `oldest_session_days` | Age in days of the oldest unarchived session log |
| `retrieval_depth_avg` | Mean `retrieval_depth` from `_metrics/` runs that touched this room |
| `lines_loaded_avg` | Mean `total_lines` from runs that touched this room |
| `feedback_pass_rate` | `pass` / total feedback count for runs touching this room (null if no feedback) |
| `feedback_fail_rate` | `fail` / total feedback count (null if no feedback) |

"Touches this room" = metrics file has a `files_read` entry whose path starts
with the room's path relative to the palace root.

---

## Scoring

Each room receives one of four statuses. Rules are evaluated in priority order
— the first match wins.

### `critical`

Any of:
- `main_lines` > 200 (hard limit from `spec/size-limits.md`)
- `max_specialty_lines` > 300
- `feedback_fail_rate` > 0.3 (more than 30% of runs rated fail)

### `degraded`

Any of:
- `main_lines` > 150 (approaching limit — consolidation needed)
- `session_log_count` > 5 (consolidation trigger from `spec/write-modes.md`)
- `oldest_session_days` > 30 (stale session logs not yet consolidated)
- `retrieval_depth_avg` > 3.5 for Type A runs (navigation is slow)
- `feedback_fail_rate` > 0.15

### `stale`

All of:
- `session_log_count` == 0
- No `_metrics/` entries for this room in the last 90 days (or no metrics at all)
- `main_lines` < 10

Indicates a room that was created but never actively used.

### `healthy`

None of the above conditions met.

---

## Palace-Level Signals

After scoring all rooms, compute aggregate signals:

| Signal | Derivation |
|---|---|
| `total_rooms` | Count of discovered rooms |
| `critical_count` | Rooms with status `critical` |
| `degraded_count` | Rooms with status `degraded` |
| `stale_count` | Rooms with status `stale` |
| `healthy_count` | Rooms with status `healthy` |
| `unstructured_count` | Dirs without a matching main file |
| `index_lines` | Line count of `INDEX.md` |
| `global_pass_rate` | `pass` / total feedback across all runs (null if no feedback) |
| `global_fail_rate` | `fail` / total feedback |

---

## Recommended Actions

Each room status maps to a set of suggested actions. The audit produces a
prioritised action list (critical first, then degraded, then stale).

| Status | Condition | Action |
|---|---|---|
| `critical` | `main_lines` > 200 | Run `/locus-consolidate` on this room |
| `critical` | `max_specialty_lines` > 300 | Split the oversized specialty file |
| `critical` | `feedback_fail_rate` > 0.3 | Review room structure and INDEX.md description |
| `degraded` | `session_log_count` > 5 | Run `/locus-consolidate` on this room |
| `degraded` | `retrieval_depth_avg` > 3.5 | Improve INDEX.md description for this room |
| `degraded` | `oldest_session_days` > 30 | Archive or consolidate stale session logs |
| `stale` | All stale conditions | Consider archiving or deleting this room |
| Any | `index_lines` > 50 | Trim INDEX.md — entry point is over the 50-line limit |
| Any | `unstructured_count` > 0 | Add main `.md` files or restructure unnamed directories |

---

## Audit Trigger Conditions

The locus skill should surface an audit suggestion at the end of a run when
any of the following are true:

- Any room accessed in the current run has `session_log_count` > 5
- Any room accessed in the current run has `main_lines` > 150
- The run's `retrieval_depth` > 3 for a Type A query (already in suggestion
  logic — audit provides deeper diagnosis)
- `_metrics/` contains 20+ runs since the last audit (first-run: always suggest)

The last-audit timestamp is stored in `_metrics/_last-audit.txt` (single ISO
8601 line). The audit skill writes this file on completion.

---

## Algorithm Complexity

The audit is O(n) in palace files — it reads each file once for line counts
and scans `_metrics/` once. For palaces with hundreds of rooms and thousands
of metrics files, a full audit may take several seconds. The audit skill may
accept a `--room <path>` argument to scope to a single room.
