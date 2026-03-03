"""
bench-compare.py — Palace vs Flat recall benchmark via live MCP.

Runs identical recall scenarios against two palaces:
  - palace:      tests/fixtures/palace   (hierarchical rooms + session logs)
  - flat-palace: tests/fixtures/flat-palace  (single 184-line MEMORY.md)

Each scenario represents an agent optimally navigating to answer a specific
question. Measures: lines loaded, tool calls, answer found.

Usage:
    uv run scripts/bench-compare.py
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PALACE = Path(__file__).parent.parent / "tests" / "fixtures" / "palace"
FLAT = Path(__file__).parent.parent / "tests" / "fixtures" / "flat-palace"


# ---------------------------------------------------------------------------
# Scenario definition
# ---------------------------------------------------------------------------

Step = tuple[str, dict]  # (tool_name, args)


@dataclass
class Scenario:
    """A recall question with pre-defined optimal navigation paths for each palace."""
    id: str
    question: str
    answer: str                 # string that must appear in responses to count as found
    palace_steps: list[Step]
    flat_steps: list[Step]
    note: str = ""              # optional annotation for the report


# Shared preamble: both palaces start with discovery
_PALACE_ROOM = [
    ("memory_list", {}),
    ("memory_list", {"path": "projects/homelab-iac"}),
]
_FLAT_ROOT = [
    ("memory_list", {}),
]


SCENARIOS: list[Scenario] = [
    # --- Specific queries: palace reads one targeted file ---

    Scenario(
        id="k3s-postgres",
        question="How do you configure K3s with external PostgreSQL?",
        answer="--datastore-endpoint",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/technical-gotchas.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="grafana-version",
        question="What version of Grafana is deployed?",
        answer="12.3.3",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/platform-services.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="1password-vip",
        question="What is the 1Password Connect VIP address?",
        answer="192.168.2.72",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/homelab-iac.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="metallb-pool",
        question="What IP pool does MetalLB use?",
        answer="192.168.2.201-250",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/platform-services.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="pg-checkpoint",
        question="How do you speed up pg_basebackup?",
        answer="--checkpoint=fast",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/technical-gotchas.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="flux-bootstrap",
        question="How do you rotate the Flux bootstrap secret?",
        answer="kubectl patch",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/homelab-iac.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),
    Scenario(
        id="keycloak-realm",
        question="What is the Keycloak realm name and PostgreSQL VIP?",
        answer="homelab",
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/platform-services.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
    ),

    # --- Session query: only palace has this (not consolidated into flat yet) ---

    Scenario(
        id="session-n8n",
        question="What work was done in the most recent session?",
        answer="n8n",
        palace_steps=_PALACE_ROOM + [
            ("memory_list", {"path": "projects/homelab-iac/sessions"}),
            ("memory_read", {"path": "projects/homelab-iac/sessions/2026-02-25.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
        note="session-only: not yet consolidated into flat",
    ),

    # --- Broad query: needs two specialty files (palace's weak case) ---

    Scenario(
        id="broad-infra",
        question="List K3s gotchas AND all deployed service versions.",
        answer="--cluster-init",   # in gotchas; full answer spans both files
        palace_steps=_PALACE_ROOM + [
            ("memory_read", {"path": "projects/homelab-iac/technical-gotchas.md"}),
            ("memory_read", {"path": "projects/homelab-iac/platform-services.md"}),
        ],
        flat_steps=_FLAT_ROOT + [
            ("memory_read", {"path": "MEMORY.md"}),
        ],
        note="broad: palace loads two specialty files",
    ),
]


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    found: bool
    lines_loaded: int
    tool_calls: int
    latency_ms: float


async def run_scenario(session: ClientSession, steps: list[Step], answer: str) -> RunResult:
    total_lines = 0
    found = False
    t0 = time.perf_counter()

    for tool, args in steps:
        resp = await session.call_tool(tool, args)
        text = resp.content[0].text if resp.content else ""
        total_lines += text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        if answer in text:
            found = True

    return RunResult(
        found=found,
        lines_loaded=total_lines,
        tool_calls=len(steps),
        latency_ms=(time.perf_counter() - t0) * 1000,
    )


@asynccontextmanager
async def mcp_session(palace: Path) -> AsyncIterator[ClientSession]:
    params = StdioServerParameters(
        command="uv",
        args=["run", "-m", "locus.mcp.main", "--palace", str(palace)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def print_report(
    scenarios: list[Scenario],
    palace_results: list[RunResult],
    flat_results: list[RunResult],
) -> None:
    W = 22

    print("\n" + "=" * 78)
    print("  RECALL BENCHMARK: Palace vs Flat")
    print("=" * 78)
    print(f"\n{'Scenario':<{W}}  {'Palace':^22}  {'Flat':^22}  {'Lines saved':>12}")
    print(f"{'':─<{W}}  {'':─<22}  {'':─<22}  {'':─<12}")
    print(f"{'':>{W}}  {'lines / calls / found':^22}  {'lines / calls / found':^22}")
    print()

    total_palace_lines = total_flat_lines = 0
    total_palace_calls = total_flat_calls = 0
    palace_found = flat_found = 0

    for s, p, f in zip(scenarios, palace_results, flat_results):
        delta = f.lines_loaded - p.lines_loaded
        delta_pct = 100 * delta / f.lines_loaded if f.lines_loaded else 0
        p_found = "✓" if p.found else "✗"
        f_found = "✓" if f.found else "✗"

        palace_col = f"{p.lines_loaded:>5} / {p.tool_calls} / {p_found}"
        flat_col   = f"{f.lines_loaded:>5} / {f.tool_calls} / {f_found}"

        note = f"  ({s.note})" if s.note else ""
        if not f.found and p.found:
            saved_col = "palace only"
        elif delta > 0:
            saved_col = f"−{delta} (−{delta_pct:.0f}%)"
        elif delta < 0:
            saved_col = f"+{-delta} (+{-delta_pct:.0f}%)"
        else:
            saved_col = "even"

        print(f"{s.id:<{W}}  {palace_col:<22}  {flat_col:<22}  {saved_col:>12}{note}")

        total_palace_lines += p.lines_loaded
        total_flat_lines   += f.lines_loaded
        total_palace_calls += p.tool_calls
        total_flat_calls   += f.tool_calls
        palace_found += int(p.found)
        flat_found   += int(f.found)

    n = len(scenarios)
    total_delta = total_flat_lines - total_palace_lines
    total_pct = 100 * total_delta / total_flat_lines if total_flat_lines else 0

    print()
    print(f"{'─'*78}")
    print(f"{'Totals':<{W}}  "
          f"{total_palace_lines:>5} / {total_palace_calls} / {palace_found}/{n}   "
          f"{total_flat_lines:>5} / {total_flat_calls} / {flat_found}/{n}")
    print()
    avg_delta = total_delta / n
    print(f"Average lines saved per query:  {avg_delta:+.0f}  ({total_pct:+.0f}% vs flat)")
    print(f"Tool call overhead per query:   "
          f"+{(total_palace_calls - total_flat_calls) / n:.1f} calls "
          f"(palace navigates, flat bulk-loads)")
    print()


async def main() -> None:
    print("Spawning palace MCP server...")
    async with mcp_session(PALACE) as palace_session:
        print("Spawning flat MCP server...")
        async with mcp_session(FLAT) as flat_session:
            palace_results: list[RunResult] = []
            flat_results:   list[RunResult] = []

            for s in SCENARIOS:
                pr = await run_scenario(palace_session, s.palace_steps, s.answer)
                fr = await run_scenario(flat_session,   s.flat_steps,   s.answer)
                palace_results.append(pr)
                flat_results.append(fr)
                print(f"  {s.id:<22}  palace={pr.lines_loaded}L/{pr.tool_calls}c {'✓' if pr.found else '✗'}  "
                      f"flat={fr.lines_loaded}L/{fr.tool_calls}c {'✓' if fr.found else '✗'}")

    print_report(SCENARIOS, palace_results, flat_results)


if __name__ == "__main__":
    asyncio.run(main())
