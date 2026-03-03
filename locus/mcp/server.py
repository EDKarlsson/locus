"""Locus MCP server — exposes the memory palace via the Model Context Protocol.

Tools
-----
memory_list   List the palace index or a room's files.
memory_read   Read any file within the palace.
memory_write  Atomically write a file within the palace (guarded).
memory_search Full-text search across the palace or a sub-path.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from locus.mcp.palace import assert_writable, safe_resolve

log = logging.getLogger("locus.mcp.server")

# The palace root is injected at server startup via `create_server()`.
_palace_root: Path | None = None

mcp = FastMCP("locus")


def _root() -> Path:
    if _palace_root is None:
        raise RuntimeError("Palace root not initialised — call create_server() first.")
    return _palace_root


# ---------------------------------------------------------------------------
# memory_list
# ---------------------------------------------------------------------------

@mcp.tool()
def memory_list(path: str = "") -> str:
    """List the palace index or the files within a room.

    Call without ``path`` (or with an empty string) to retrieve ``INDEX.md``,
    the top-level routing table for the palace.  Pass a relative room path
    (e.g. ``"global/networking"``) to list the markdown files in that room.
    """
    root = _root()
    log.debug("memory_list path=%r", path or "(index)")

    if not path or path.strip() == "":
        index = root / "INDEX.md"
        if index.is_file():
            log.debug("returning INDEX.md (%d bytes)", index.stat().st_size)
            return _read_bounded(index, "INDEX.md")
        log.warning("INDEX.md not found at palace root: %s", root)
        return f"No INDEX.md found at palace root: {root}"

    target = safe_resolve(root, path)

    if target.is_file():
        log.debug("memory_list returning file contents: %s", target)
        return _read_bounded(target, path)

    if not target.is_dir():
        log.info("memory_list: path not found: %s", path)
        return f"Path not found: {path}"

    entries = sorted(target.iterdir())
    log.debug("memory_list listing %d entries in %s", len(entries), target)
    lines = [f"# {target.relative_to(root)}\n"]
    for entry in entries:
        rel = entry.relative_to(root)
        kind = "/" if entry.is_dir() else ""
        lines.append(f"- {rel}{kind}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# memory_read
# ---------------------------------------------------------------------------

@mcp.tool()
def memory_read(path: str) -> str:
    """Read a file from the palace.

    ``path`` is relative to the palace root (e.g. ``"global/networking/networking.md"``).
    Returns the full file contents as a string.
    """
    root = _root()
    log.debug("memory_read path=%r", path)
    target = safe_resolve(root, path)

    if not target.exists():
        log.info("memory_read: file not found: %s", path)
        return f"File not found: {path}"
    if target.is_dir():
        log.info("memory_read: path is a directory: %s", path)
        return f"'{path}' is a directory — use memory_list to browse it."

    return _read_bounded(target, path)


# ---------------------------------------------------------------------------
# memory_write
# ---------------------------------------------------------------------------

@mcp.tool()
def memory_write(path: str, content: str) -> str:
    """Write content to a file within the palace.

    ``path`` is relative to the palace root.  The write is atomic (write to a
    temp file, then rename).  Writes to ``_metrics/``, ``sessions/``, or
    ``archived/`` are rejected, as are non-text file extensions.

    Creates parent directories as needed.
    """
    root = _root()
    log.debug("memory_write path=%r len=%d", path, len(content))
    target = safe_resolve(root, path)
    assert_writable(root, target)   # raises ValueError (logged by FastMCP) if blocked

    byte_len = len(content.encode("utf-8"))
    if byte_len > _MAX_WRITE_BYTES:
        raise ValueError(
            f"Content too large ({byte_len:,} bytes, limit {_MAX_WRITE_BYTES:,} bytes)"
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write via temp file in same directory (same filesystem).
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
    except Exception as exc:
        log.error("memory_write failed for %s: %s", path, exc)
        if tmp is not None:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass
        raise

    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    log.info("memory_write: wrote %d lines to %s", lines, path)
    return f"Written {lines} lines to {path}"


# ---------------------------------------------------------------------------
# memory_search
# ---------------------------------------------------------------------------

@mcp.tool()
def memory_search(query: str, path: str = "") -> str:
    """Full-text search across the palace (or a sub-path).

    Uses ripgrep (``rg``) if available; falls back to Python ``re``.
    Returns up to 20 matches, each showing the relative file path, line
    number, and matched line with 1 line of context on each side.

    ``path`` narrows the search to a specific room or subdirectory.
    """
    root = _root()
    log.debug("memory_search query=%r path=%r", query, path or "(palace root)")
    search_root = safe_resolve(root, path) if path and path.strip() else root

    if not search_root.exists():
        log.info("memory_search: search path not found: %s", path)
        return f"Search path not found: {path}"

    try:
        result = _search_rg(query, search_root, root)
        log.debug("memory_search: rg backend, %d result lines", result.count("\n"))
        return result
    except FileNotFoundError:
        log.info("memory_search: rg not found, falling back to Python re")
        result = _search_python(query, search_root, root)
        log.debug("memory_search: python backend, %d result lines", result.count("\n"))
        return result


def _search_rg(query: str, search_root: Path, palace_root: Path) -> str:
    """Ripgrep-backed search (JSON output for unambiguous path parsing)."""
    import json as _json

    result = subprocess.run(
        [
            "rg",
            "--type", "md",
            "--json",
            "--context", "1",
            "--max-count", "5",
            "--max-filesize", "500K",
            "--", query,
            str(search_root),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if not result.stdout.strip():
        return f"No matches for '{query}'"

    lines: list[str] = []
    prev_path: str | None = None

    for raw_line in result.stdout.splitlines():
        try:
            obj = _json.loads(raw_line)
        except _json.JSONDecodeError:
            continue

        kind = obj.get("type")
        if kind == "begin":
            path = obj["data"]["path"]["text"]
            try:
                rel = str(Path(path).relative_to(palace_root))
            except ValueError:
                rel = path
            if prev_path and prev_path != rel:
                lines.append("--")
            prev_path = rel

        elif kind in ("match", "context"):
            data = obj["data"]
            path = data["path"]["text"]
            try:
                rel = str(Path(path).relative_to(palace_root))
            except ValueError:
                rel = path
            lineno = data["line_number"]
            text = data["lines"]["text"].rstrip("\n")
            sep = ":" if kind == "match" else "-"
            lines.append(f"{rel}{sep}{lineno}{sep}{text}")

        if len(lines) >= 200:
            break

    return "\n".join(lines) if lines else f"No matches for '{query}'"


_MAX_READ_BYTES = 500_000   # 500 KB — palace files should be tiny
_MAX_WRITE_BYTES = 500_000  # 500 KB — guards against runaway writes
_MAX_QUERY_LEN = 200


def _read_bounded(path: Path, rel: str) -> str:
    """Read ``path`` and return its text, or an error if it exceeds _MAX_READ_BYTES."""
    size = path.stat().st_size
    if size > _MAX_READ_BYTES:
        log.warning("file too large (%d bytes): %s", size, rel)
        return f"File too large to read ({size:,} bytes, limit {_MAX_READ_BYTES:,} bytes): {rel}"
    return path.read_text(encoding="utf-8")


def _search_python(query: str, search_root: Path, palace_root: Path) -> str:
    """Python re fallback search.

    Queries are treated as literals (not regexes) to prevent ReDoS — MCP
    clients send natural language, not patterns.  Query length is capped to
    bound worst-case scanning time.
    """
    if len(query) > _MAX_QUERY_LEN:
        return f"Query too long ({len(query)} chars, max {_MAX_QUERY_LEN})"
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    results: list[str] = []
    md_files = sorted(search_root.rglob("*.md"))

    for md_file in md_files:
        if len(results) >= 20:
            break
        try:
            text_lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(text_lines):
            if pattern.search(line):
                rel = md_file.relative_to(palace_root)
                context_before = text_lines[i - 1] if i > 0 else ""
                context_after = text_lines[i + 1] if i < len(text_lines) - 1 else ""
                block = [
                    f"{rel}:{i + 1}:{line}",
                ]
                if context_before:
                    results.append(f"{rel}:{i}:{context_before}")
                results.append(f"{rel}:{i + 1}:{line}")
                if context_after:
                    results.append(f"{rel}:{i + 2}:{context_after}")
                results.append("--")
                if len(results) >= 20:
                    break

    if not results:
        return f"No matches for '{query}'"
    return "\n".join(results[:200])


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def create_server(palace_root: Path) -> FastMCP:
    """Initialise the server with a palace root and return it."""
    global _palace_root
    _palace_root = palace_root
    log.info("server initialised with palace: %s", palace_root)
    return mcp
