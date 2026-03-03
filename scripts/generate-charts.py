"""
generate-charts.py — Generate benchmark charts for docs/img/.

Can use live data from bench run JSON files, or falls back to hardcoded
baseline data if no files are supplied.

Usage:
    # Hardcoded baseline (always works):
    uv run scripts/generate-charts.py

    # From live bench runs:
    uv run scripts/bench-mcp.py     --json-out /tmp/mcp.json
    uv run scripts/bench-compare.py --json-out /tmp/compare.json
    uv run scripts/generate-charts.py --mcp-run /tmp/mcp.json --compare-run /tmp/compare.json

Outputs:
  docs/img/lines-comparison.svg    — palace vs flat lines loaded per scenario
  docs/img/latency-by-category.svg — MCP tool latency by category
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent.parent / "docs" / "img"

# Palette
PALACE_COLOR = "#2563EB"
FLAT_COLOR   = "#F97316"
SAVE_COLOR   = "#16A34A"
MISS_COLOR   = "#DC2626"
GRID_COLOR   = "#F1F5F9"
TEXT_COLOR   = "#1E293B"

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.edgecolor":    "#CBD5E1",
    "axes.linewidth":    0.8,
    "text.color":        TEXT_COLOR,
    "axes.labelcolor":   TEXT_COLOR,
    "xtick.color":       TEXT_COLOR,
    "ytick.color":       TEXT_COLOR,
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "grid.color":        GRID_COLOR,
    "grid.linewidth":    1.0,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})


# ---------------------------------------------------------------------------
# Data loading — JSON first, hardcoded fallback
# ---------------------------------------------------------------------------

def load_compare_data(path: Path | None) -> dict:
    """Load bench-compare.py JSON output, or return hardcoded baseline."""
    if path and path.exists():
        raw = json.loads(path.read_text())
        scenarios = raw["scenarios"]
        return {
            "ids":          [s["id"] for s in scenarios],
            "palace_lines": [s["palace"]["lines"] for s in scenarios],
            "flat_lines":   [s["flat"]["lines"] for s in scenarios],
            "flat_found":   [s["flat"]["found"] for s in scenarios],
        }
    # Baseline from 2026-03-02 run
    return {
        "ids": [
            "k3s-postgres", "grafana-version", "1password-vip", "metallb-pool",
            "pg-checkpoint", "flux-bootstrap", "keycloak-realm", "session-n8n", "broad-infra",
        ],
        "palace_lines": [95, 86, 83, 86, 95, 83, 86, 55, 153],
        "flat_lines":   [191, 191, 191, 191, 191, 191, 191, 191, 191],
        "flat_found":   [True, True, True, True, True, True, True, False, True],
    }


def load_mcp_data(path: Path | None) -> dict:
    """Load bench-mcp.py JSON output, or return hardcoded baseline."""
    if path and path.exists():
        raw = json.loads(path.read_text())
        cats = raw["categories"]
        return {
            "categories":  list(cats.keys()),
            "avg_ms":      [cats[c]["avg_ms"] for c in cats],
            "case_counts": [cats[c]["total"] for c in cats],
            "p95_ms":      raw["overall"]["p95_ms"],
        }
    # Baseline from 2026-03-02 run
    return {
        "categories":  ["navigation", "write", "fidelity", "edge", "search", "safety"],
        "avg_ms":      [5.2, 5.5, 6.6, 7.5, 13.7, 2.0],
        "case_counts": [8, 4, 5, 6, 8, 9],
        "p95_ms":      15.8,
    }


# ---------------------------------------------------------------------------
# Chart functions
# ---------------------------------------------------------------------------

SHORT_LABEL_MAP = {
    "k3s-postgres":    "k3s\npostgres",
    "grafana-version": "grafana\nversion",
    "1password-vip":   "1password\nvip",
    "metallb-pool":    "metallb\npool",
    "pg-checkpoint":   "pg\ncheckpoint",
    "flux-bootstrap":  "flux\nbootstrap",
    "keycloak-realm":  "keycloak\nrealm",
    "session-n8n":     "session\nn8n",
    "broad-infra":     "broad\ninfra",
}


def chart_lines_comparison(data: dict, out: Path) -> None:
    ids          = data["ids"]
    palace_lines = data["palace_lines"]
    flat_lines   = data["flat_lines"]
    flat_found   = data["flat_found"]
    labels       = [SHORT_LABEL_MAP.get(i, i) for i in ids]

    x     = np.arange(len(ids))
    width = 0.38

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.18)

    ax.bar(x - width / 2, palace_lines, width, color=PALACE_COLOR,
           label="Palace", zorder=3, linewidth=0)
    ax.bar(x + width / 2, flat_lines,   width, color=FLAT_COLOR,
           label="Flat (MEMORY.md)", zorder=3, linewidth=0)

    for i, (pl, fl, found) in enumerate(zip(palace_lines, flat_lines, flat_found)):
        pct = round(100 * (fl - pl) / fl)
        ax.text(x[i] - width / 2, pl + 2, f"−{pct}%",
                ha="center", va="bottom", fontsize=8.5,
                color=SAVE_COLOR, fontweight="bold")

    for i, found in enumerate(flat_found):
        if not found:
            ax.text(x[i] + width / 2, flat_lines[i] + 2, "✗ miss",
                    ha="center", va="bottom", fontsize=8.5,
                    color=MISS_COLOR, fontweight="bold")

    avg_p = sum(palace_lines) / len(palace_lines)
    avg_f = sum(flat_lines)   / len(flat_lines)
    ax.axhline(avg_p, color=PALACE_COLOR, linestyle="--", linewidth=1.2, alpha=0.7, zorder=2)
    ax.axhline(avg_f, color=FLAT_COLOR,   linestyle="--", linewidth=1.2, alpha=0.7, zorder=2)
    ax.text(len(ids) - 0.1, avg_p + 3, f"avg {avg_p:.0f}L",
            color=PALACE_COLOR, fontsize=8.5, ha="right")
    ax.text(len(ids) - 0.1, avg_f + 3, f"avg {avg_f:.0f}L",
            color=FLAT_COLOR,   fontsize=8.5, ha="right")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Lines loaded into context")
    ax.set_title("Context Load: Palace vs Flat Memory")
    ax.set_ylim(0, 230)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=10)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out.relative_to(Path.cwd())}")


def chart_latency(data: dict, out: Path) -> None:
    pairs = sorted(zip(data["avg_ms"], data["categories"], data["case_counts"]))
    avg_ms_s, cats_s, counts_s = zip(*pairs)
    p95 = data["p95_ms"]

    y          = np.arange(len(cats_s))
    bar_colors = [PALACE_COLOR if ms < 10 else FLAT_COLOR for ms in avg_ms_s]

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.subplots_adjust(left=0.16, right=0.93, top=0.88, bottom=0.12)

    ax.barh(y, avg_ms_s, color=bar_colors, height=0.55, zorder=3, linewidth=0)

    for i, (ms, count) in enumerate(zip(avg_ms_s, counts_s)):
        ax.text(ms + 0.2, i, f"{ms} ms  ({count} cases)",
                va="center", fontsize=9.5, color=TEXT_COLOR)

    ax.set_yticks(y)
    ax.set_yticklabels(cats_s, fontsize=10)
    ax.set_xlabel("Average round-trip latency (ms)")
    ax.set_title(f"MCP Tool Latency by Category  ·  p95 = {p95} ms")
    ax.set_xlim(0, 22)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    fast = mpatches.Patch(color=PALACE_COLOR, label="< 10 ms")
    slow = mpatches.Patch(color=FLAT_COLOR,   label="≥ 10 ms  (rg subprocess)")
    ax.legend(handles=[fast, slow], loc="lower right", framealpha=0.9, fontsize=9)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out.relative_to(Path.cwd())}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mcp-run",     metavar="PATH",
                        help="bench-mcp.py --json-out file to use for latency chart")
    parser.add_argument("--compare-run", metavar="PATH",
                        help="bench-compare.py --json-out file to use for lines chart")
    parser.add_argument("--out-dir",     metavar="DIR", default=str(OUT),
                        help="Output directory for SVG files (default: docs/img/)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    compare_data = load_compare_data(Path(args.compare_run) if args.compare_run else None)
    mcp_data     = load_mcp_data(Path(args.mcp_run)     if args.mcp_run     else None)

    source = "live data" if (args.mcp_run or args.compare_run) else "hardcoded baseline"
    print(f"Generating charts from {source}...")

    chart_lines_comparison(compare_data, out_dir / "lines-comparison.svg")
    chart_latency(mcp_data,              out_dir / "latency-by-category.svg")
    print("Done.")


if __name__ == "__main__":
    main()
