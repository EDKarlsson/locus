# Palace Health Report Format

Defines the output of `locus-audit`. The report is written to
`_metrics/audit-YYYY-MM-DDTHHMMSSZ.md` within the palace and also
printed to stdout when run interactively.

---

## File Location

```
palace/
  _metrics/
    audit-2026-03-02T143012Z.md   ← human-readable report
    _last-audit.txt               ← single ISO 8601 line (last audit timestamp)
```

`_last-audit.txt` is updated on every successful audit completion. The audit
skill reads it to determine whether an audit suggestion is due.

---

## Report Structure

```markdown
# Palace Health Report

Audited: 2026-03-02T14:30:12Z
Palace: /path/to/palace
Rooms: 5 total — 1 critical, 1 degraded, 0 stale, 3 healthy

---

## Summary

| Metric | Value |
|---|---|
| INDEX.md lines | 21 / 50 (✅ healthy) |
| Total rooms | 5 |
| Critical | 1 |
| Degraded | 1 |
| Stale | 0 |
| Healthy | 3 |
| Unstructured dirs | 0 |
| Metrics runs analysed | 12 |
| Global pass rate | 87% (13/15 rated runs) |
| Global fail rate | 0% |

---

## Action Items

Priority-ordered. Address critical items before degraded.

1. 🔴 **[critical]** `projects/api-platform` — main file 215 lines (limit: 200). Run `/locus-consolidate projects/api-platform`.
2. 🟡 **[degraded]** `projects/data-pipeline` — 7 unprocessed session logs (threshold: 5). Run `/locus-consolidate projects/data-pipeline`.
3. 🟡 **[degraded]** `projects/data-pipeline` — avg retrieval depth 4.2 for Type A queries (threshold: 3.5). Review INDEX.md description for this room.

---

## Per-Room Detail

### `projects/api-platform` 🔴 critical

| Signal | Value | Status |
|---|---|---|
| main_lines | 215 | ❌ over limit (200) |
| specialty_files | 3 | ✅ |
| max_specialty_lines | 180 | ✅ |
| session_log_count | 2 | ✅ |
| oldest_session_days | 5 | ✅ |
| retrieval_depth_avg | 2.8 | ✅ |
| feedback_pass_rate | 100% | ✅ |
| feedback_fail_rate | 0% | ✅ |

**Actions:**
- Run `/locus-consolidate projects/api-platform` to merge session logs and prune main file.

---

### `projects/data-pipeline` 🟡 degraded

| Signal | Value | Status |
|---|---|---|
| main_lines | 88 | ✅ |
| specialty_files | 2 | ✅ |
| max_specialty_lines | 95 | ✅ |
| session_log_count | 7 | ⚠️ over threshold (5) |
| oldest_session_days | 22 | ✅ |
| retrieval_depth_avg | 4.2 | ⚠️ over threshold (3.5) |
| feedback_pass_rate | 75% | ✅ |
| feedback_fail_rate | 8% | ✅ |

**Actions:**
- Run `/locus-consolidate projects/data-pipeline` to process 7 session logs.
- Improve INDEX.md description for this room to reduce navigation depth.

---

### `global/toolchain` ✅ healthy

| Signal | Value | Status |
|---|---|---|
| main_lines | 45 | ✅ |
| session_log_count | 1 | ✅ |
| retrieval_depth_avg | 2.1 | ✅ |
| feedback_pass_rate | 100% | ✅ |

---

<!-- repeat for each room -->
```

---

## Status Icons

| Icon | Status | Meaning |
|---|---|---|
| 🔴 | `critical` | Immediate action required — size limit exceeded or high fail rate |
| 🟡 | `degraded` | Action recommended — approaching limits or slow navigation |
| ⚪ | `stale` | Room exists but shows no usage — consider archiving |
| ✅ | `healthy` | All signals within thresholds |

---

## Minimal Report (no metrics data)

When `_metrics/` is empty or absent, the report omits retrieval and feedback
signals and notes the gap:

```markdown
# Palace Health Report

Audited: 2026-03-02T14:30:12Z
Palace: /path/to/palace
Note: no _metrics/ data found — retrieval and feedback signals skipped.
Run at least one `locus` query to enable full health analysis.

Rooms: 3 total — 0 critical, 0 degraded, 0 stale, 3 healthy
```

Structure-only signals (file sizes, session counts) are always evaluated.

---

## Machine-Readable Sidecar

The audit also writes `_metrics/audit-YYYY-MM-DDTHHMMSSZ.json` alongside
the markdown report. Schema:

```json
{
  "schema_version": "1",
  "audited_at": "2026-03-02T14:30:12Z",
  "palace_path": "/path/to/palace",
  "index_lines": 21,
  "rooms": [
    {
      "path": "projects/api-platform",
      "status": "critical",
      "signals": {
        "main_lines": 215,
        "specialty_files": 3,
        "max_specialty_lines": 180,
        "session_log_count": 2,
        "oldest_session_days": 5,
        "retrieval_depth_avg": 2.8,
        "feedback_pass_rate": 1.0,
        "feedback_fail_rate": 0.0
      },
      "actions": [
        "Run /locus-consolidate projects/api-platform"
      ]
    }
  ],
  "summary": {
    "total_rooms": 5,
    "critical": 1,
    "degraded": 1,
    "stale": 0,
    "healthy": 3,
    "unstructured_dirs": 0,
    "metrics_runs_analysed": 12,
    "global_pass_rate": 0.87,
    "global_fail_rate": 0.0
  },
  "action_items": [
    {"priority": 1, "status": "critical", "room": "projects/api-platform", "action": "Run /locus-consolidate projects/api-platform"}
  ]
}
```
