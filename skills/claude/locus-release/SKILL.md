---
name: locus-release
description: Post-release verification for locus-mcp. Run after tagging and pushing a new version to ensure all documents, tests, and charts are consistent with the release.
---

# locus-release

Post-release verification skill for the `locus` project. Run this after every version
tag to catch stale version strings, prevent test regressions, and keep benchmark charts
current.

## When to use

- After `git tag vX.Y.Z && git push origin vX.Y.Z`
- After merging a version-bump PR
- Whenever docs/img/ charts may be stale (benchmark scripts changed, new tools added)

## Steps

### 1. Read pyproject.toml to get the current version

```python
version = <value of [project].version in pyproject.toml>
```

### 2. Run unit tests — MUST NOT regress

```bash
uv run pytest tests/unit/ -q
```

- If any tests fail, stop. Do not proceed until the regression is fixed.
- Record the test count. If it decreased vs the previous release, investigate.

### 3. Verify version strings in docs

Check the following files contain the current version (or auto-updating badges):

| File | What to check |
|---|---|
| `CHANGELOG.md` | Has an entry for `## vX.Y.Z` |
| `README.md` | Roadmap table includes `vX.Y` milestone as Complete |
| `Dockerfile` | `ARG LOCUS_MCP_VERSION="X.Y.Z"` matches current version |
| `pyproject.toml` | Source of truth — already read in Step 1 |

If any file is stale, update it and commit with the version bump PR (not separately).

### 4. Re-run MCP integration benchmark

```bash
# Requires: locus-mcp running on stdio (uses subprocess internally)
uv run python scripts/bench-mcp.py 2>&1 | tail -5
```

- All 40 cases must pass. If any fail, investigate before releasing.
- Record avg latency and p95. Flag if p95 > 50ms (latency regression).

### 5. Re-run palace vs flat benchmark

```bash
uv run python scripts/bench-compare.py 2>&1 | tail -10
```

- Palace pass rate must be ≥ 87% (baseline from v0.6.0).
- Flat miss rate must be ≥ 13% on Type C queries (regression if flat improves on Type C
  means palace lost its structural advantage).

### 6. Regenerate charts

```bash
uv run python scripts/generate-charts.py
```

- Regenerates `docs/img/lines-comparison.svg` and `docs/img/latency-by-category.svg`.
- Stage and include in the release commit or a follow-up `chore(docs): update charts`.

### 7. Verify spec/mcp-server.md is current

- Transport section should list all available transports.
- Configuration examples should use current env var names.
- No "not implemented in vX.Y" stubs referring to already-shipped features.

### 8. Summary checklist

```
[ ] uv run pytest tests/unit/ — N tests, 0 failures
[ ] CHANGELOG.md has vX.Y.Z entry
[ ] README.md roadmap includes vX.Y milestone
[ ] Dockerfile ARG matches version
[ ] bench-mcp.py: 40/40 pass, p95 < 50ms
[ ] bench-compare.py: palace ≥ 87% pass
[ ] docs/img/ charts regenerated
[ ] spec/mcp-server.md current
```

## Notes

- The PyPI badge in README is dynamic and auto-updates — no manual change needed.
- Registry entries (Glama, PulseMCP) auto-ingest from PyPI weekly — no action needed.
- Official MCP Registry (`server.json`) should be updated manually if the transport
  or package entry changes significantly.
