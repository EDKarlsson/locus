# Size Limits and Context Thresholds

Context discipline is the core design constraint of Locus. Every limit here
exists to keep the agent's working context small while ensuring the right
information is always reachable.

## File Size Limits

| File type | Soft limit | Hard limit | Action when exceeded |
|---|---|---|---|
| `INDEX.md` | 40 lines | 50 lines | Split into sub-indices per domain |
| Room main file | 150 lines | 200 lines | Extract sections into specialty files |
| Specialty file | 200 lines | 300 lines | Split into more granular files |
| Session log | No limit | — | Consolidate after session ends |
| Canonical fact file | 100 lines | 150 lines | Split by sub-topic |

**Why 200 lines for room main files?**
The Claude auto-memory system truncates always-loaded files at ~200 lines.
This is a hard technical constraint, not a style preference — content beyond
200 lines is invisible to the agent.

## Token Estimation

When performance metrics are enabled, estimate tokens as: `lines × 15`.
This is a rough heuristic (English prose averages ~10–20 tokens/line).
Accurate token counts require a tokeniser; line counts are language-agnostic
and sufficient for threshold decisions.

| Lines | Estimated tokens |
|---|---|
| 50 | ~750 |
| 100 | ~1,500 |
| 200 | ~3,000 |
| 300 | ~4,500 |

## Retrieval Depth Thresholds

Retrieval depth = number of files read to answer a single query.

| Depth | Assessment | Recommended action |
|---|---|---|
| 1–2 files | Healthy | No action |
| 3–4 files | Acceptable | Monitor |
| 5+ files | Degraded | Restructure — rooms may be too granular or INDEX.md too vague |

## Consolidation Triggers

Consolidation should be considered when any of the following are true:

- A room's main file exceeds its soft limit
- A session log directory contains more than 5 unprocessed logs
- The same room was accessed in 3 or more consecutive sessions
- A retrieval required reading 5+ files

## INDEX.md Budget

The INDEX.md must fit in 50 lines. Budget breakdown:

```
Header + description:     3 lines
Global rooms table:      ~10 lines (header + up to 7 rooms)
Per-project rooms table: ~15 lines (header + up to 12 rooms)
Metadata footer:          2 lines
Buffer:                  20 lines
```

If the palace grows beyond this budget, introduce sub-indices:
`global/INDEX.md` and `projects/<name>/INDEX.md`, with the root
`INDEX.md` pointing to them.
