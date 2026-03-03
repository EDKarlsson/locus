# Locus Feedback

Record quality feedback on the most recent Locus run. Annotates the run's
metrics file with a user verdict so retrieval quality can be tracked over time.

**Usage:** `locus-feedback <quality> [note]`

**Arguments:**
- `quality` (required) — `pass`, `partial`, or `fail` (aliases: `good`/`ok`/`bad`)
- `note` (optional) — free-text explanation

**Examples:**
```
locus-feedback pass
locus-feedback partial "Got the right room but missed the port number"
locus-feedback fail "Answered about the wrong service entirely"
```

---

## Steps

### 1. Resolve quality value

Map the first argument to a canonical value:
- `pass` or `good` → `"pass"`
- `partial` or `ok` → `"partial"`
- `fail` or `bad` → `"fail"`

If missing or unrecognized, stop and print:
```
Usage: locus-feedback <pass|partial|fail> [note]
```

### 2. Find the palace root

Walk up from cwd looking for a directory containing both `INDEX.md` and `_metrics/`.

If not found:
```
Error: no palace found (no _metrics/ directory above current path).
Run from inside a palace directory.
```

### 3. Find the most recent metrics file

```bash
ls -t <palace_root>/_metrics/*.json | head -1
```

If empty:
```
Error: no metrics files found in <palace_root>/_metrics/.
Run a locus query first to generate a metrics file.
```

### 4. Read and validate

```bash
cat <metrics_file>
```

Check `feedback` field is `null`. If already set, warn and overwrite.

### 5. Write feedback

Update the `feedback` field in-place using `python3 -c`:

```bash
python3 -c "
import json, sys
from datetime import datetime, timezone

data = json.load(open('$METRICS_FILE'))
data['feedback'] = {
    'quality': '$QUALITY',
    'note': $NOTE_JSON,
    'recorded_at': datetime.now(timezone.utc).isoformat()
}
json.dump(data, open('$METRICS_FILE', 'w'), indent=2)
"
```

### 6. Report

```
Locus feedback recorded: <quality> → _metrics/<filename>
```
