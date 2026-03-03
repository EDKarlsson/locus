"""CLI entry point for the Locus MCP server.

Usage
-----
    locus-mcp [--palace PATH] [--transport {stdio,sse}]

If ``--palace`` is omitted the server resolves the palace root via
``LOCUS_PALACE`` env var, ``.locus/`` in CWD, or ``~/.locus/``.

For SSE transport, set ``FASTMCP_HOST`` / ``FASTMCP_PORT`` env vars to
control the bind address (defaults: 0.0.0.0:8000).  If ``LOCUS_API_KEY``
is set, every request must carry ``Authorization: Bearer <key>``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from locus.mcp.palace import find_palace
from locus.mcp.server import create_server

log = logging.getLogger("locus.mcp")


# ---------------------------------------------------------------------------
# Auth middleware (SSE transport only)
# ---------------------------------------------------------------------------

class BearerAuthMiddleware:
    """ASGI middleware that enforces a static Bearer token on all requests."""

    def __init__(self, app, api_key: str) -> None:
        self._app = app
        self._key = api_key

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self._key}":
                await self._reject(scope, send)
                return
        await self._app(scope, receive, send)

    @staticmethod
    async def _reject(scope, send) -> None:
        if scope["type"] == "http":
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({"type": "http.response.body", "body": b"Unauthorized"})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

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
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport to use (default: stdio; use sse for network deployments)",
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

    if args.transport == "sse":
        import uvicorn

        app = server.sse_app()

        api_key = os.environ.get("LOCUS_API_KEY")
        if api_key:
            log.info("API key auth enabled")
            app = BearerAuthMiddleware(app, api_key)
        else:
            log.warning("LOCUS_API_KEY not set — SSE endpoint is unauthenticated")

        host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
        port = int(os.environ.get("FASTMCP_PORT", "8000"))
        log.info("starting SSE server on %s:%d", host, port)
        uvicorn.run(app, host=host, port=port)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    cli()
