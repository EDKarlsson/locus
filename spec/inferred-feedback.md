# Inferred Feedback

Defines how the Locus skill detects implicit disagreement signals from user
messages and automatically records feedback without requiring `/locus-feedback`.

Explicit feedback (`/locus-feedback pass|partial|fail`) always takes
precedence over inferred feedback. Inference only fires when no explicit
feedback has been recorded for the most recent run.

---

## When Inference Runs

After giving a Locus-sourced answer, the skill watches the **immediate
follow-up user message** (the next message in the conversation) for
disagreement signals. If a signal is found before the user starts a new
unrelated task, the skill auto-records feedback on the most recent
`_metrics/*.json` file.

Inference is scoped to the first follow-up only — it does not scan
earlier messages or multi-turn exchanges.

---

## Signal Classification

Messages are classified into three outcomes:

| Class | Quality recorded | Description |
|---|---|---|
| `fail` | `"fail"` | Strong disagreement — user asserts the answer was wrong |
| `partial` | `"partial"` | Mild correction — answer was incomplete or slightly off |
| `none` | (no feedback) | No disagreement detected |

### `fail` patterns

The message (lowercased, stripped) matches any of:

- `that's wrong` / `that is wrong`
- `that's incorrect` / `that is incorrect`
- `that's not right` / `that is not right`
- `you got that wrong`
- `incorrect`
- `wrong answer`
- `no, that` (followed by contradiction)
- `not correct`

### `partial` patterns

The message matches any of:

- starts with `actually`
- starts with `not quite`
- `almost, but` / `close, but` / `almost right`
- `you missed` / `you're missing`
- `that's not complete` / `incomplete`
- `that didn't answer` / `doesn't answer my question`
- `not what I` / `not what i`
- `try again`
- `that's only part`

### False-positive guards

Do **not** record inferred feedback if:

- The follow-up message is longer than 300 characters (likely a new task,
  not a correction)
- The follow-up contains a URL, code block, or file path (new content, not feedback)
- A `/locus-feedback` command was already run for this run
- The `feedback` field in the most recent metrics file is already non-null

---

## Confidence Scoring

The classifier returns a confidence value (0.0–1.0) alongside the class.

| Confidence | Meaning |
|---|---|
| 1.0 | Exact match on a `fail` pattern |
| 0.8 | Exact match on a `partial` pattern |
| 0.6 | Partial match (pattern found within a longer message ≤ 300 chars) |

Only results with confidence ≥ 0.6 are recorded. The confidence value is
stored in the feedback note: `"inferred (confidence: 0.8) — <original message>"`.

---

## Integration Points

1. **`locus` skill (Step 7)** — after giving an answer, check the next
   user message with `classify_message()`. If non-null result, call the
   feedback recording logic from `locus-feedback`.

2. **`locus-audit`** — when computing `feedback_fail_rate` and
   `feedback_pass_rate`, inferred feedback entries are counted identically
   to explicit ones (same schema, `feedback.quality` field).

3. **`locus-feedback` CLI / skill** — explicit feedback always overwrites
   an inferred entry (last-write wins on the `feedback` key).
