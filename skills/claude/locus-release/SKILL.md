---
name: locus-release
description: Post-release verification for locus-mcp. Run after tagging and pushing a new version to ensure all documents, tests, and charts are consistent with the release.
scope: dev
audience: contributors
---

# locus-release

> **Project development only.** This skill operates on the `locus` source repository.
> It is not part of the palace interface and should not be invoked from within the MCP
> server or against a user's palace directory. End users of `locus-mcp` do not need
> this skill.

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
# Write structured JSON results — avoids relying on text output format
uv run python scripts/bench-mcp.py --json-out /tmp/bench-mcp-results.json
```

Then verify from the JSON:
```python
import json
r = json.load(open("/tmp/bench-mcp-results.json"))
assert r["summary"]["passed"] == 40, f"Expected 40, got {r['summary']['passed']}"
assert r["summary"]["p95_ms"] < 50, f"p95 latency regression: {r['summary']['p95_ms']}ms"
```

- All 40 cases must pass. If any fail, investigate before releasing.
- Flag if p95 > 50ms (latency regression; current baseline is ~16ms).

### 5. Re-run palace vs flat benchmark

```bash
uv run python scripts/bench-compare.py --json-out /tmp/bench-compare-results.json
```

Then verify from the JSON:
```python
import json
r = json.load(open("/tmp/bench-compare-results.json"))
palace_pass = r["palace"]["pass_rate"]
assert palace_pass >= 0.87, f"Palace pass rate regression: {palace_pass:.0%}"
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

### 8. Verify README badges

Check all four badges in `README.md` are correct:

| Badge | Expected |
|---|---|
| CI | Points to `.github/workflows/ci.yml` on `Nano-Nimbus/locus` |
| PyPI version | Slug is `locus-mcp`; auto-updates from PyPI — verify the link resolves to the correct package |
| Python version | Matches `requires-python` in `pyproject.toml` (currently `3.11+`) |
| License | Matches the `LICENSE` file (currently MIT) |

The PyPI badge is dynamic — if it shows a stale version after release, PyPI propagation
takes a few minutes. Wait and refresh before concluding it is broken.

### 9. Verify PyPI publish

After the tag push triggers `publish.yml`:

```bash
# Check the workflow completed successfully
gh run list --workflow=publish.yml --limit=3

# Confirm the new version is live on PyPI
curl -s https://pypi.org/pypi/locus-mcp/json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('latest:', d['info']['version'])
print('all versions:', list(d['releases'].keys())[-5:])
"
```

The version reported must match `pyproject.toml`. If `publish.yml` failed, check
for the Docker/PyPI race condition (see MEMORY.md release gotchas) — rerun docker.yml
after PyPI propagates.

### 10. Verify GHCR image

After `docker.yml` completes:

```bash
# Confirm the image tag exists on GHCR
gh api /orgs/Nano-Nimbus/packages/container/locus-mcp/versions \
  --jq '.[] | {tags: .metadata.container.tags, created: .created_at}' | head -20
```

Expected: a version entry with tag `X.Y.Z` (and optionally `latest`).

Also verify `Dockerfile` `ARG LOCUS_MCP_VERSION` matches the release version:

```bash
grep "ARG LOCUS_MCP_VERSION" Dockerfile
```

### 11. Summary checklist

```
[ ] uv run pytest tests/unit/ — N tests, 0 failures
[ ] CHANGELOG.md has vX.Y.Z entry
[ ] README.md roadmap includes vX.Y milestone
[ ] README.md badges: CI workflow URL correct, PyPI slug correct, Python version matches pyproject.toml
[ ] Dockerfile ARG LOCUS_MCP_VERSION matches release version
[ ] PyPI: locus-mcp X.Y.Z live at pypi.org/project/locus-mcp/
[ ] GHCR: ghcr.io/nano-nimbus/locus-mcp:X.Y.Z image published
[ ] bench-mcp.py: 40/40 pass, p95 < 50ms
[ ] bench-compare.py: palace ≥ 87% pass
[ ] docs/img/ charts regenerated
[ ] spec/mcp-server.md current
```

## Notes

- Registry entries (Glama, PulseMCP) auto-ingest from PyPI weekly — no action needed.
- Official MCP Registry (`server.json`) should be updated manually if the transport
  or package entry changes significantly.
- Docker/PyPI race: if `docker.yml` fails immediately after a tag push, wait for PyPI
  to propagate (~2 min) then rerun the Docker workflow via `gh run rerun <run-id>`.
