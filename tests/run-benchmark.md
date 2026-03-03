# Locus Benchmark

Measures context efficiency and answer quality: Locus palace navigation
vs the flat baseline. Run after any significant change to the palace structure
or navigation skill.

---

## Query Set

15 queries across three types. IDs are stable — use them in results files.

### Type A: Specific fact lookup
Single answer, lives in one file. Tests retrieval precision.

| ID | Query |
|----|-------|
| A1 | What is the K3s API server endpoint URL? |
| A2 | What version of Keycloak is deployed and what namespace is it in? |
| A3 | What is the MetalLB IP address pool range? |
| A4 | What storage class should be used for NFS-backed persistent volumes? |
| A5 | What is the 1Password Connect VIP address and port? |

### Type B: Cross-domain queries
Answer spans multiple files or requires combining facts. Tests navigation depth.

| ID | Query |
|----|-------|
| B1 | What Tailscale and K3s integration gotchas exist? |
| B2 | How is 1Password Connect set up and what are its known gotchas? |
| B3 | What backup services are running and how is PostgreSQL backed up? |
| B4 | How does the Flux GitOps dependency chain work and what are its failure modes? |
| B5 | What is the full monitoring stack (versions, components, notable config)? |

### Type C: Recency queries
Answer is in or near session logs. Tests session log discovery.

| ID | Query |
|----|-------|
| C1 | What was worked on in the most recent session? |
| C2 | What findings from recent sessions should be promoted to canonical files? |
| C3 | What changed between v0.155.0 and the current version? |

### Type D: Troubleshooting queries
Maps directly to gotchas. Tests specialty file targeting.

| ID | Query |
|----|-------|
| D1 | Terraform plan is hanging after a VM create. What is the likely cause and fix? |
| D2 | K3s registry mirror returns HTTP 400. What is the fix? |
| D3 | An ExternalSecret is not syncing even after the 1Password item was created. Why? |

---

## Running the Benchmark

### Automated (Agent SDK)

Run each query against both fixtures and record metrics:

```sh
# Palace run
locus --palace tests/fixtures/palace \
      --task "<query text>" \
      --metrics-file tests/results/<RUN_DATE>-palace-<ID>.json

# Flat run (agent loads flat/MEMORY.md, no palace navigation)
locus --palace tests/fixtures/flat \
      --task "<query text>" \
      --metrics-file tests/results/<RUN_DATE>-flat-<ID>.json
```

Collect all results into a run summary:

```sh
python -c "
import json, glob, sys
date = sys.argv[1]
for f in sorted(glob.glob(f'tests/results/{date}-*.json')):
    d = json.load(open(f))
    print(f\"{f}: depth={d['retrieval_depth']} lines={d['total_lines']}\")
" <RUN_DATE>
```

### Manual

For each query:
1. Note the query ID and text.
2. **Palace run:** Starting only with INDEX.md, navigate to the relevant room(s).
   Record every file you read and its line count.
3. **Flat run:** Load `tests/fixtures/flat/MEMORY.md` (184 lines, always full).
   Note that retrieval depth is always 1.
4. For both runs: score answer quality (see below).
5. Record in a results file (see template below).

---

## Scoring Answer Quality

| Score | Meaning |
|---|---|
| ✅ Pass | Correct, complete answer with specific values (IPs, versions, commands) |
| ⚠️ Partial | Correct direction but missing specifics, or requires a follow-up read |
| ❌ Fail | Wrong answer, missing entirely, or agent states it doesn't know |

---

## Results Template

Copy to `tests/results/YYYY-MM-DD.md` for each benchmark run.

```markdown
# Benchmark Run YYYY-MM-DD

Agent: <claude-sonnet-4-x / codex / gemini>
Fixture versions: flat=184 lines, palace=INDEX(21)+main(55)+gotchas(67)+services(58)

## Summary

| Metric | Flat | Palace | Delta |
|---|---|---|---|
| Avg retrieval depth (files) | | | |
| Avg lines loaded | | | |
| Pass rate | | | |

## Per-Query Results

### A1 — K3s API server endpoint URL

**Palace:**
- Files read: `INDEX.md` (21), `projects/homelab-iac/homelab-iac.md` (55)
- Lines loaded: 76
- Answer quality: ✅ / ⚠️ / ❌
- Answer: <what the agent returned>

**Flat:**
- Files read: `MEMORY.md` (184)
- Lines loaded: 184
- Answer quality: ✅ / ⚠️ / ❌
- Answer: <what the agent returned>

**Observation:** <any notes>

---
<!-- repeat for each query ID -->
```

---

## Interpreting Results

**Retrieval depth delta** — palace should read fewer files for Type A queries.
For Type B and D, depth may be equal but content quality should be higher.

**Lines loaded delta** — palace should load fewer lines for all Type A queries.
Type B queries may be comparable; this is expected and acceptable.

**Pass rate delta** — palace should not degrade answer quality. If palace
scores lower than flat on any query, investigate whether INDEX.md is
descriptive enough or whether the room structure needs adjustment.

**When to act:**
- Palace retrieval depth > 3 for any Type A query → INDEX.md description needs improvement
- Palace lines loaded > flat for any Type A query → room structure issue
- Palace pass rate < flat for any query type → navigation skill needs refinement
