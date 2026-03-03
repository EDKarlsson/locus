# Metrics Schema

Defines the JSON format for Locus run metrics and where they are stored
within a palace. All tools that read or write metrics (Agent SDK, feedback
skill, suggestion logic) use this schema.

---

## Storage

Metrics files live in a `_metrics/` directory at the palace root:

```
palace/
  _metrics/
    2026-03-02T143012Z.json   ← one file per run
    2026-03-02T151847Z.json
  INDEX.md
  projects/
    ...
```

**Filename format:** `YYYY-MM-DDTHHMMSSZ.json` (UTC, compact ISO 8601, no colons — safe on all filesystems).

**`_metrics/` conventions:**
- Underscore prefix marks it as a system directory — not a knowledge room, never navigated or consolidated.
- Not included in `INDEX.md`. Not subject to room size limits.
- Not committed to git by default (add `palace/_metrics/` to `.gitignore` if privacy matters).

When the Agent SDK CLI is invoked with `--metrics-file <path>`, that path overrides the default. Use this for benchmark runs where output goes to `tests/results/`.

---

## Schema (v1)

```json
{
  "schema_version": "1",
  "palace_path": "/absolute/path/to/palace",
  "task": "What is the K3s API server endpoint?",
  "query_type": null,
  "agent": {
    "model": "claude-sonnet-4-6",
    "sdk_version": "0.1.44"
  },
  "started_at": "2026-03-02T14:30:12Z",
  "finished_at": "2026-03-02T14:30:58Z",
  "retrieval_depth": 3,
  "total_lines": 134,
  "estimated_tokens": 2010,
  "total_cost_usd": 0.0023,
  "files_read": [
    {"path": "INDEX.md", "lines": 21},
    {"path": "projects/api-platform/api-platform.md", "lines": 55},
    {"path": "projects/api-platform/platform-services.md", "lines": 58}
  ],
  "feedback": null,
  "suggestions": []
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | `"1"` | Schema version. Increment on breaking changes. |
| `palace_path` | string | Absolute path to palace root passed to the agent. |
| `task` | string | The query or task string. |
| `query_type` | `"A"` \| `"B"` \| `"C"` \| `"D"` \| `null` | Optional benchmark query type. Null for non-benchmark runs. |
| `agent.model` | string \| null | Model ID as reported by the SDK (e.g. `claude-sonnet-4-6`). |
| `agent.sdk_version` | string \| null | `claude-agent-sdk` package version. |
| `started_at` | ISO 8601 string | UTC timestamp when the run began. |
| `finished_at` | ISO 8601 string \| null | UTC timestamp when the run completed. Null if aborted. |
| `retrieval_depth` | integer | Number of files read during the run. |
| `total_lines` | integer | Sum of line counts across all files read. |
| `estimated_tokens` | integer | `total_lines × 15` — rough token estimate (see `spec/size-limits.md`). |
| `total_cost_usd` | float \| null | API cost reported by the SDK. Null if unavailable. |
| `files_read` | array of `{path, lines}` | Ordered list of files the agent read. `lines` is null for binary files. |
| `feedback` | object \| null | Quality feedback appended by `/locus feedback`. Null until feedback is recorded. |
| `suggestions` | array of strings | Structural suggestions generated during the run. Empty if none. |

### `feedback` object

Populated by the `/locus feedback` skill (see `#14`). Null until the user runs feedback.

```json
{
  "quality": "pass",
  "note": "Returned the exact IP and port.",
  "recorded_at": "2026-03-02T14:32:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `quality` | `"pass"` \| `"partial"` \| `"fail"` | User-rated answer quality. Maps to ✅/⚠️/❌ from the benchmark rubric. |
| `note` | string \| null | Optional free-text note. |
| `recorded_at` | ISO 8601 string | UTC timestamp when feedback was recorded. |

---

## Health Thresholds

Used by suggestion logic (see `#15`). These are the conditions under which
the agent should surface a structural suggestion to the user.

| Condition | Threshold | Likely cause | Suggested action |
|---|---|---|---|
| Type A retrieval depth | > 3 files | INDEX.md description too vague | Improve room description in INDEX.md |
| Type A lines loaded | > flat baseline (184) | Room structure too broad | Split specialty files or prune main file |
| Any pass rate drop | palace < flat for same query | Navigation skill miscalibrated | Review INDEX.md or skill protocol |
| Retrieval depth | > 5 for any query | Deep nesting or missing sub-index | Add sub-index or flatten room |

For non-benchmark runs (no `query_type`), depth > 4 triggers a generic suggestion.

---

## Versioning

- `schema_version` is a plain integer string (`"1"`, `"2"`, ...).
- Additive changes (new nullable fields) do not require a version bump.
- Removing or renaming fields requires incrementing to `"2"`.
- Consumers should treat unknown fields as no-ops.
