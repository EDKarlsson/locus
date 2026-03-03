"""Palace root resolution and path-safety utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger("locus.mcp.palace")

# Directories that MCP clients may not write to.
_WRITE_BLOCKED_DIRS = {"_metrics", "sessions", "archived"}

# Extensions permitted for memory_write.
_WRITABLE_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}


def find_palace(palace_arg: str | None = None) -> Path:
    """Resolve the palace root.

    Priority:
    1. Explicit ``--palace`` argument
    2. ``LOCUS_PALACE`` environment variable
    3. ``.locus/`` in the current working directory
    4. ``~/.locus/`` global palace
    """
    if palace_arg:
        p = Path(palace_arg).expanduser().resolve()
        if not p.is_dir():
            raise ValueError(f"Palace path does not exist: {p}")
        log.debug("palace resolved from --palace arg: %s", p)
        return p

    env = os.environ.get("LOCUS_PALACE")
    if env:
        p = Path(env).expanduser().resolve()
        if not p.is_dir():
            raise ValueError(f"LOCUS_PALACE does not exist: {p}")
        log.debug("palace resolved from LOCUS_PALACE env: %s", p)
        return p

    cwd_locus = Path.cwd() / ".locus"
    if cwd_locus.is_dir():
        log.debug("palace resolved from .locus/ in cwd: %s", cwd_locus.resolve())
        return cwd_locus.resolve()

    home_locus = Path.home() / ".locus"
    if home_locus.is_dir():
        log.debug("palace resolved from ~/.locus: %s", home_locus.resolve())
    else:
        _bootstrap_palace(home_locus)
        log.info("palace bootstrapped at %s", home_locus)
    _ensure_index(home_locus)
    return home_locus.resolve()


_INDEX_TEMPLATE = """\
# Memory Palace

Personal memory palace — cross-project facts, tooling notes, and session knowledge.

## Global Rooms

| Room | Description | Path |
|---|---|---|

## Project Rooms

| Room | Description | Path |
|---|---|---|

---
_Last consolidated: {date}_

<!--
NAVIGATION: Read this file first. Identify the relevant room(s), then read
only those. Do not load the full palace. If no room matches your query,
check whether a new room is warranted before writing to an existing one.

SIZE LIMIT: Keep this file under 50 lines.
-->
"""


def _bootstrap_palace(palace: Path) -> None:
    """Create a minimal palace directory structure."""
    for subdir in ("global", "projects"):
        (palace / subdir).mkdir(parents=True, exist_ok=True)
    log.info("created palace directories at %s", palace)


def _ensure_index(palace: Path) -> None:
    """Write INDEX.md if it doesn't exist yet."""
    index = palace / "INDEX.md"
    if not index.exists():
        from datetime import date
        index.write_text(
            _INDEX_TEMPLATE.format(date=date.today().isoformat()),
            encoding="utf-8",
        )
        log.info("created %s", index)


def safe_resolve(palace_root: Path, rel_path: str) -> Path:
    """Resolve ``rel_path`` within ``palace_root``, rejecting traversal.

    Raises ``ValueError`` if the resolved path escapes the palace root.
    """
    # Normalise: strip leading slashes so absolute paths don't escape.
    clean = rel_path.lstrip("/")
    resolved = (palace_root / clean).resolve()
    try:
        resolved.relative_to(palace_root)
    except ValueError:
        raise ValueError(
            f"Path '{rel_path}' escapes the palace root '{palace_root}'"
        )
    return resolved


def assert_writable(palace_root: Path, target: Path) -> None:
    """Raise ``ValueError`` if ``target`` is in a write-blocked directory or
    has a non-writable extension."""
    # Check every path segment — blocked dirs are forbidden at any depth.
    rel = target.relative_to(palace_root)
    for part in rel.parts[:-1]:  # exclude the filename itself
        if part in _WRITE_BLOCKED_DIRS:
            raise ValueError(
                f"Writes to '{part}/' are not permitted via MCP. "
                "Use the locus-feedback or locus-audit tools instead."
            )
    if target.suffix not in _WRITABLE_EXTENSIONS:
        raise ValueError(
            f"Extension '{target.suffix}' is not writable via MCP. "
            f"Allowed: {', '.join(sorted(_WRITABLE_EXTENSIONS))}"
        )
