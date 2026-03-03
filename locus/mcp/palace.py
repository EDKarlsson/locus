"""Palace root resolution and path-safety utilities."""

from __future__ import annotations

import os
from pathlib import Path

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
        return p

    env = os.environ.get("LOCUS_PALACE")
    if env:
        p = Path(env).expanduser().resolve()
        if not p.is_dir():
            raise ValueError(f"LOCUS_PALACE does not exist: {p}")
        return p

    cwd_locus = Path.cwd() / ".locus"
    if cwd_locus.is_dir():
        return cwd_locus.resolve()

    home_locus = Path.home() / ".locus"
    if home_locus.is_dir():
        return home_locus.resolve()

    raise ValueError(
        "No palace found. Pass --palace, set LOCUS_PALACE, or create .locus/ "
        "in the current directory."
    )


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
