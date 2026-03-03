# Benchmark Fixtures

Two versions of the same homelab-iac knowledge base for measuring Locus's
context efficiency vs the naive flat approach.

## Structure

```
flat/
  MEMORY.md          184 lines — everything in one file (always loaded)

palace/
  INDEX.md            21 lines — palace entry point (always loaded)
  projects/homelab-iac/
    homelab-iac.md    55 lines — room main file
    technical-gotchas.md  67 lines — K3s, Terraform, Flux, 1Password, PG, Ansible
    platform-services.md  58 lines — service versions, IPs, URLs
    sessions/
      2026-02-25.md   24 lines — sample session log with consolidation notes
```

## Hypothesis

For specific queries, Locus loads less context than flat while returning
more targeted information.

| Query type | Flat | Palace files loaded | Palace lines |
|---|---|---|---|
| K3s gotchas | 184 lines | INDEX + main + gotchas | 143 lines (−22%) |
| Service version | 184 lines | INDEX + main + services | 134 lines (−27%) |
| Broad (gotchas + services) | 184 lines | INDEX + main + both | 201 lines (+9%) |

**Key insight:** For broad queries, palace may load slightly more lines but
the content is better organized for the agent. In a real palace with 8+
specialty files, the savings on specific queries are substantially larger
— the agent skips 5-6 irrelevant files entirely.

## flat-palace

`flat-palace/` is used by `scripts/bench-compare.py` as the comparison target.
It is a minimal palace containing:
- `INDEX.md` — 6-line index pointing to `MEMORY.md`
- `MEMORY.md` — **a copy of `flat/MEMORY.md`** (184 lines, all knowledge in one file)

> **Note:** `flat-palace/MEMORY.md` is a copy, not a symlink. If `flat/MEMORY.md`
> is updated, `flat-palace/MEMORY.md` must be updated to match or the comparison
> benchmark will be testing against stale data.

## Benchmark Runner

See `tests/run-benchmark.md` for the query set and how to run the benchmark.
Results are written to `tests/results/`.
