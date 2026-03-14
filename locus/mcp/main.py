"""CLI entry point for the Locus MCP server.

Usage
-----
    locus-mcp [--palace PATH] [--transport {stdio,sse}]

If ``--palace`` is omitted the server resolves the palace root via
``LOCUS_PALACE`` env var, ``.locus/`` in CWD, or ``~/.locus/``.

For SSE transport, set ``FASTMCP_HOST`` / ``FASTMCP_PORT`` env vars to
control the bind address (defaults: 127.0.0.1:8000).  If ``LOCUS_API_KEY``
is set, every request must carry ``Authorization: Bearer <key>``.

Environment variables (SSE transport)
--------------------------------------
FASTMCP_HOST          Bind address (default: 127.0.0.1)
FASTMCP_PORT          Bind port (default: 8000)
LOCUS_API_KEY         Bearer token required on all requests (recommended)
LOCUS_ALLOWED_HOSTS   Comma-separated extra hostnames allowed in the HTTP
                      Host header, in addition to the loopback defaults
                      (127.0.0.1:*, localhost:*, [::1]:*).  Required when
                      running behind a reverse proxy (Tailscale, K8s ingress)
                      whose Host header differs from localhost.
                      Supports the FastMCP :* wildcard port syntax.
                      Example: "myhost.ts.net,myservice.svc.cluster.local:*"
"""

from __future__ import annotations

import argparse
import importlib.metadata
import logging
import os
import secrets
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
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if not secrets.compare_digest(auth, f"Bearer {self._key}"):
                await self._reject(send)
                return
        await self._app(scope, receive, send)

    @staticmethod
    async def _reject(send) -> None:
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"text/plain"],
                [b"www-authenticate", b'Bearer realm="locus-mcp"'],
            ],
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
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('locus-mcp')}",
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
    parser.add_argument(
        "--security",
        action="store_true",
        default=False,
        help=(
            "Enable file signature verification and auto-signing. "
            "Requires locus-security.yaml in the palace root and initialized keys."
        ),
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
    server = create_server(palace, security=args.security)

    if args.transport == "sse":
        import uvicorn
        from mcp.server.transport_security import TransportSecuritySettings

        # Build allowed_hosts: always include loopback; extend with
        # LOCUS_ALLOWED_HOSTS (comma-separated) for reverse-proxy deployments
        # where the Host header will be an external hostname (e.g. Tailscale FQDN).
        _ALLOWED_HOSTS_ENV = "LOCUS_ALLOWED_HOSTS"
        _DEFAULT_ALLOWED_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        extra_hosts = [
            h.strip()
            for h in os.environ.get(_ALLOWED_HOSTS_ENV, "").split(",")
            if h.strip()
        ]
        allowed_hosts = _DEFAULT_ALLOWED_HOSTS + extra_hosts
        server.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
        )
        log.info("allowed hosts: %s", allowed_hosts)

        app = server.sse_app()

        api_key = os.environ.get("LOCUS_API_KEY")
        if api_key:
            log.info("API key auth enabled")
            app = BearerAuthMiddleware(app, api_key)
        else:
            log.warning("LOCUS_API_KEY not set — SSE endpoint is unauthenticated")

        host = os.environ.get("FASTMCP_HOST", "127.0.0.1")

        port_str = os.environ.get("FASTMCP_PORT")
        if port_str is None:
            port = 8000
        else:
            try:
                port = int(port_str)
            except ValueError:
                log.error("Invalid FASTMCP_PORT %r — must be an integer; using 8000", port_str)
                port = 8000

        log.info("starting SSE server on %s:%d", host, port)
        uvicorn.run(app, host=host, port=port, log_config=None, log_level=args.log_level.lower())
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    cli()
