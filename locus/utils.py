"""Shared utilities used across locus sub-packages."""

from __future__ import annotations

from pathlib import Path


def slug_from_path(p: Path) -> str:
    """Convert an absolute path to a Claude Code project slug.

    Claude Code derives project slugs by replacing every ``/`` with ``-``.
    The leading ``/`` becomes a leading ``-``.

    Example: ``/home/user/git/myproject`` → ``-home-user-git-myproject``
    """
    return str(p).replace("/", "-")
