"""CLI entry point for the Locus MCP server.

Usage
-----
    locus-mcp [--palace PATH]

If ``--palace`` is omitted the server resolves the palace root via
``LOCUS_PALACE`` env var, ``.locus/`` in CWD, or ``~/.locus/``.
"""

from __future__ import annotations

import argparse

from locus.mcp.palace import find_palace
from locus.mcp.server import create_server


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Locus MCP server — memory palace via Model Context Protocol"
    )
    parser.add_argument(
        "--palace",
        metavar="PATH",
        default=None,
        help="Path to the palace root directory",
    )
    args = parser.parse_args()

    try:
        palace = find_palace(args.palace)
    except ValueError as exc:
        parser.error(str(exc))

    server = create_server(palace)
    server.run(transport="stdio")


if __name__ == "__main__":
    cli()
