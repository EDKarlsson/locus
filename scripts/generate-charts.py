"""
generate-charts.py — Generate benchmark charts for docs/img/.

Uses data from the most recent bench-compare.py and bench-mcp.py runs.
Run with: uv run scripts/generate-charts.py

Outputs:
  docs/img/lines-comparison.svg   — palace vs flat lines loaded per scenario
  docs/img/latency-by-category.svg — MCP tool latency by category
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = Path(__file__).parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# Palette
PALACE_COLOR = "#2563EB"   # blue
FLAT_COLOR   = "#F97316"   # orange
SAVE_COLOR   = "#16A34A"   # green
MISS_COLOR   = "#DC2626"   # red
GRID_COLOR   = "#F1F5F9"
TEXT_COLOR   = "#1E293B"

plt.rcParams.update({
    "font.family":      "sans-serif",
    "font.size":        11,
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
    "axes.edgecolor":   "#CBD5E1",
    "axes.linewidth":   0.8,
    "text.color":       TEXT_COLOR,
    "axes.labelcolor":  TEXT_COLOR,
    "xtick.color":      TEXT_COLOR,
    "ytick.color":      TEXT_COLOR,
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "grid.color":       GRID_COLOR,
    "grid.linewidth":   1.0,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})


# ---------------------------------------------------------------------------
# Chart 1: Lines loaded — Palace vs Flat
# ---------------------------------------------------------------------------

SCENARIOS = [
    "k3s-postgres",
    "grafana-version",
    "1password-vip",
    "metallb-pool",
    "pg-checkpoint",
    "flux-bootstrap",
    "keycloak-realm",
    "session-n8n",
    "broad-infra",
]

PALACE_LINES = [95, 86, 83, 86, 95, 83, 86, 55, 153]
FLAT_LINES   = [191, 191, 191, 191, 191, 191, 191, 191, 191]
FLAT_FOUND   = [True, True, True, True, True, True, True, False, True]  # ✗ = session-n8n

SHORT_LABELS = [
    "k3s\npostgres",
    "grafana\nversion",
    "1password\nvip",
    "metallb\npool",
    "pg\ncheckpoint",
    "flux\nbootstrap",
    "keycloak\nrealm",
    "session\nn8n",
    "broad\ninfra",
]

x = np.arange(len(SCENARIOS))
width = 0.38

fig, ax = plt.subplots(figsize=(12, 5))
fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.18)

bars_palace = ax.bar(x - width / 2, PALACE_LINES, width, color=PALACE_COLOR,
                     label="Palace", zorder=3, linewidth=0)
bars_flat   = ax.bar(x + width / 2, FLAT_LINES,   width, color=FLAT_COLOR,
                     label="Flat (MEMORY.md)", zorder=3, linewidth=0)

# Annotate savings on palace bars
for i, (pl, fl, found) in enumerate(zip(PALACE_LINES, FLAT_LINES, FLAT_FOUND)):
    saved_pct = round(100 * (fl - pl) / fl)
    ax.text(x[i] - width / 2, pl + 2, f"−{saved_pct}%",
            ha="center", va="bottom", fontsize=8.5,
            color=SAVE_COLOR, fontweight="bold")

# Mark flat "not found" bar
miss_idx = FLAT_FOUND.index(False)
ax.text(x[miss_idx] + width / 2, FLAT_LINES[miss_idx] + 2, "✗ miss",
        ha="center", va="bottom", fontsize=8.5, color=MISS_COLOR, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(SHORT_LABELS, fontsize=9)
ax.set_ylabel("Lines loaded into context")
ax.set_title("Context Load: Palace vs Flat Memory")
ax.set_ylim(0, 230)
ax.yaxis.grid(True, zorder=0)
ax.set_axisbelow(True)

avg_palace = sum(PALACE_LINES) / len(PALACE_LINES)
avg_flat   = sum(FLAT_LINES)   / len(FLAT_LINES)
ax.axhline(avg_palace, color=PALACE_COLOR, linestyle="--", linewidth=1.2,
           alpha=0.7, zorder=2)
ax.axhline(avg_flat,   color=FLAT_COLOR,   linestyle="--", linewidth=1.2,
           alpha=0.7, zorder=2)
ax.text(len(SCENARIOS) - 0.1, avg_palace + 3, f"avg {avg_palace:.0f}L",
        color=PALACE_COLOR, fontsize=8.5, ha="right")
ax.text(len(SCENARIOS) - 0.1, avg_flat + 3,   f"avg {avg_flat:.0f}L",
        color=FLAT_COLOR,   fontsize=8.5, ha="right")

ax.legend(loc="upper right", framealpha=0.9, fontsize=10)

out = OUT / "lines-comparison.svg"
fig.savefig(out, format="svg", bbox_inches="tight")
plt.close(fig)
print(f"  wrote {out.relative_to(Path.cwd())}")


# ---------------------------------------------------------------------------
# Chart 2: MCP tool latency by category
# ---------------------------------------------------------------------------

CATEGORIES = ["navigation", "write", "fidelity", "edge", "search", "safety"]
AVG_MS      = [5.2,          5.5,     6.6,         7.5,    13.7,     2.0]
CASE_COUNTS = [8,             4,       5,            6,      8,        9]

# Sort by latency ascending
pairs = sorted(zip(AVG_MS, CATEGORIES, CASE_COUNTS))
AVG_MS_S, CATEGORIES_S, COUNTS_S = zip(*pairs)

fig, ax = plt.subplots(figsize=(8, 4))
fig.subplots_adjust(left=0.16, right=0.93, top=0.88, bottom=0.12)

y = np.arange(len(CATEGORIES_S))

bar_colors = [PALACE_COLOR if ms < 10 else FLAT_COLOR for ms in AVG_MS_S]
bars = ax.barh(y, AVG_MS_S, color=bar_colors, height=0.55, zorder=3, linewidth=0)

for i, (ms, count) in enumerate(zip(AVG_MS_S, COUNTS_S)):
    ax.text(ms + 0.2, i, f"{ms} ms  ({count} cases)",
            va="center", fontsize=9.5, color=TEXT_COLOR)

ax.set_yticks(y)
ax.set_yticklabels(CATEGORIES_S, fontsize=10)
ax.set_xlabel("Average round-trip latency (ms)")
ax.set_title("MCP Tool Latency by Category  ·  p95 = 15.8 ms")
ax.set_xlim(0, 22)
ax.xaxis.grid(True, zorder=0)
ax.set_axisbelow(True)

fast_patch = mpatches.Patch(color=PALACE_COLOR, label="< 10 ms")
slow_patch = mpatches.Patch(color=FLAT_COLOR,   label="≥ 10 ms  (rg subprocess)")
ax.legend(handles=[fast_patch, slow_patch], loc="lower right",
          framealpha=0.9, fontsize=9)

out = OUT / "latency-by-category.svg"
fig.savefig(out, format="svg", bbox_inches="tight")
plt.close(fig)
print(f"  wrote {out.relative_to(Path.cwd())}")

print("Done.")
