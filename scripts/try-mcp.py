"""Quick smoke test for the locus-mcp server.

Connects via stdio, calls all four tools, prints results.

Usage:
    uv run scripts/try-mcp.py [--palace PATH]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PALACE = Path(__file__).parent.parent / "tests/fixtures/palace"


async def run(palace: Path) -> None:
    log_level = "DEBUG" if "--debug" in sys.argv else "WARNING"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "locus.mcp.main", "--palace", str(palace), "--log-level", log_level],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Tools registered: {[t.name for t in tools.tools]}\n")

            # ── memory_list (index) ─────────────────────────────────────
            print("=" * 60)
            print("memory_list()  →  INDEX.md")
            print("=" * 60)
            r = await session.call_tool("memory_list", {})
            print(r.content[0].text[:600])

            # ── memory_list (room) ──────────────────────────────────────
            print("\n" + "=" * 60)
            print("memory_list(path='projects/homelab-iac')  →  room files")
            print("=" * 60)
            r = await session.call_tool("memory_list", {"path": "projects/homelab-iac"})
            print(r.content[0].text)

            # ── memory_read ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("memory_read('projects/homelab-iac/homelab-iac.md')  →  file contents")
            print("=" * 60)
            r = await session.call_tool(
                "memory_read", {"path": "projects/homelab-iac/homelab-iac.md"}
            )
            print(r.content[0].text[:800])

            # ── memory_write ────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("memory_write('scratch/hello.md', ...)  →  atomic write")
            print("=" * 60)
            r = await session.call_tool(
                "memory_write",
                {
                    "path": "scratch/hello.md",
                    "content": "# Hello from MCP\n\nThis file was written via locus-mcp.\n",
                },
            )
            print(r.content[0].text)
            written = (palace / "scratch" / "hello.md").read_text()
            print(f"Verified on disk: {written!r}")

            # ── memory_write guard ──────────────────────────────────────
            print("\n" + "=" * 60)
            print("memory_write('_metrics/bad.json', ...)  →  should be blocked")
            print("=" * 60)
            r = await session.call_tool(
                "memory_write",
                {"path": "_metrics/bad.json", "content": "{}"},
            )
            if r.isError:
                print(f"Blocked as expected: {r.content[0].text}")
            else:
                print("ERROR: write was NOT blocked!")

            # ── memory_search ───────────────────────────────────────────
            print("\n" + "=" * 60)
            print("memory_search('K3s')  →  full-text search")
            print("=" * 60)
            r = await session.call_tool("memory_search", {"query": "K3s"})
            print(r.content[0].text[:600])

            # Cleanup scratch dir
            import shutil
            scratch = palace / "scratch"
            if scratch.exists():
                shutil.rmtree(scratch)
            print("\n✓ All tools exercised. Scratch dir cleaned up.")


if __name__ == "__main__":
    palace = Path(sys.argv[sys.argv.index("--palace") + 1]) if "--palace" in sys.argv else PALACE
    asyncio.run(run(palace))
