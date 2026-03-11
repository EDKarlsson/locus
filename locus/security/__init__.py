"""Locus security — RSA-like prompt injection defense for AI agents.

Public surface:
    SecurityContext     — per-session state (config, keystore, nonce, taint tracker)
    build_security_context() — construct from palace root
"""

from __future__ import annotations

from pathlib import Path

from .config import load_security_config
from .keys import load_keystore
from .middleware import AuditEntry, SecurityContext, SecurityMiddleware
from .nonce import generate_session_nonce, inject_security_context
from .taint import TaintTracker

from locus.mcp.palace import _slug_from_path  # reuse existing slug utility


def build_security_context(palace_root: Path) -> SecurityContext:
    """Load config, keys, and generate session nonce for a palace root.

    Raises FileNotFoundError if locus-security.yaml or keys are missing.
    Raises ValueError if config is invalid.
    """
    palace_root = palace_root.resolve()
    config = load_security_config(palace_root)
    if config is None:
        raise FileNotFoundError(
            f"No locus-security.yaml found in {palace_root}. "
            "Create one to enable the security system."
        )

    keystore = load_keystore(config.key_store_path)
    palace_slug = _slug_from_path(palace_root)
    nonce = generate_session_nonce(palace_slug)

    return SecurityContext(
        config=config,
        keystore=keystore,
        palace_root=palace_root,
        session_nonce=nonce,
        taint_tracker=TaintTracker(),
        audit_log=[],
    )


__all__ = [
    "SecurityContext",
    "SecurityMiddleware",
    "AuditEntry",
    "build_security_context",
]
