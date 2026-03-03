"""Locus MCP server — exposes the memory palace via the Model Context Protocol.

Tools
-----
memory_list   List the palace index or a room's files.
memory_read   Read any file within the palace.
memory_write  Atomically write a file within the palace (guarded).
memory_search Full-text search across the palace or a sub-path.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from locus.mcp.palace import assert_writable, safe_resolve

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

    if not path or path.strip() == "":
        index = root / "INDEX.md"
        if index.is_file():
            return index.read_text(encoding="utf-8")
        return f"No INDEX.md found at palace root: {root}"

    target = safe_resolve(root, path)

    if target.is_file():
        return target.read_text(encoding="utf-8")

    if not target.is_dir():
        return f"Path not found: {path}"

    entries = sorted(target.iterdir())
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
    target = safe_resolve(root, path)

    if not target.exists():
        return f"File not found: {path}"
    if target.is_dir():
        return f"'{path}' is a directory — use memory_list to browse it."

    return target.read_text(encoding="utf-8")


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
    target = safe_resolve(root, path)
    assert_writable(root, target)

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
    except Exception:
        if tmp is not None:
            try:
                Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass
        raise

    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
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
    search_root = safe_resolve(root, path) if path and path.strip() else root

    if not search_root.exists():
        return f"Search path not found: {path}"

    try:
        return _search_rg(query, search_root, root)
    except FileNotFoundError:
        return _search_python(query, search_root, root)


def _search_rg(query: str, search_root: Path, palace_root: Path) -> str:
    """Ripgrep-backed search."""
    result = subprocess.run(
        [
            "rg",
            "--type", "md",
            "--line-number",
            "--context", "1",
            "--max-count", "5",       # 5 matches per file
            "--max-filesize", "500K",
            query,
            str(search_root),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if not result.stdout.strip():
        return f"No matches for '{query}'"
    return _format_rg_output(result.stdout, palace_root)


def _format_rg_output(raw: str, palace_root: Path) -> str:
    """Replace absolute paths with palace-relative paths in rg output."""
    lines = []
    for line in raw.splitlines():
        # rg output: /absolute/path/file.md:10:matched text
        if line and line[0] == "/" and ":" in line:
            parts = line.split(":", 2)
            try:
                rel = Path(parts[0]).relative_to(palace_root)
                lines.append(f"{rel}:{parts[1]}:{parts[2]}")
                continue
            except (ValueError, IndexError):
                pass
        lines.append(line)
    # Limit total output
    return "\n".join(lines[:200])


def _search_python(query: str, search_root: Path, palace_root: Path) -> str:
    """Python re fallback search."""
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as exc:
        return f"Invalid search pattern: {exc}"

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
    return mcp
