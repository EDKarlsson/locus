"""CLI entry point for the Locus MCP server.

Usage
-----
    locus-mcp [--palace PATH]

If ``--palace`` is omitted the server resolves the palace root via
``LOCUS_PALACE`` env var, ``.locus/`` in CWD, or ``~/.locus/``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from locus.mcp.palace import find_palace
from locus.mcp.server import create_server

log = logging.getLogger("locus.mcp")


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
    parser.add_argument(
        "--log-level",
        metavar="LEVEL",
        default=os.environ.get("LOCUS_MCP_LOG_LEVEL", "WARNING"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING; env: LOCUS_MCP_LOG_LEVEL)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        stream=sys.stderr,
        format="%(asctime)s [locus-mcp] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        force=True,   # override any handlers FastMCP set up on import
    )

    try:
        palace = find_palace(args.palace)
    except ValueError as exc:
        parser.error(str(exc))

    log.info("palace root: %s", palace)
    server = create_server(palace)
    server.run(transport="stdio")


if __name__ == "__main__":
    cli()
