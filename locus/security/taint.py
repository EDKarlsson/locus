"""Taint tracking for Locus security — tracks provenance of content through tool calls."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .config import CriticalityLevel, SecurityConfig
from .signing import VerificationResult

log = logging.getLogger("locus.security.taint")


class TaintLevel(str, Enum):
    TRUSTED = "TRUSTED"    # operator-signed and verified
    AUDITED = "AUDITED"    # AUDITED boundary, unverified but allowed
    TAINTED = "TAINTED"    # CRITICAL boundary violation or nonce detected
    UNKNOWN = "UNKNOWN"    # not yet classified


@dataclass
class TaintRecord:
    content_fingerprint: str   # first 16 hex chars of SHA-256 of content
    taint_level: TaintLevel
    source: str                # e.g. "memory_read:global/networking.md"
    acquired_at: str           # ISO 8601 UTC
    tag: str | None            # prefix to inject into agent context


@dataclass
class TaintTracker:
    """Per-session taint registry. Instantiated once per agent run."""

    _registry: dict[str, TaintRecord] = field(default_factory=dict)
    # Maps tool_use_id → pending taint record (set in PreToolUse, used in PostToolUse)
    _pending: dict[str, TaintRecord] = field(default_factory=dict)
    # tool_chain: (tool_name, tool_use_id, max_taint_of_inputs)
    _tool_chain: list[tuple[str, str, TaintLevel]] = field(default_factory=list)

    def register_pending(self, tool_use_id: str, record: TaintRecord) -> None:
        self._pending[tool_use_id] = record

    def pop_pending(self, tool_use_id: str) -> TaintRecord | None:
        return self._pending.pop(tool_use_id, None)

    def record(self, record: TaintRecord) -> None:
        self._registry[record.content_fingerprint] = record

    def get(self, content_fingerprint: str) -> TaintRecord | None:
        return self._registry.get(content_fingerprint)

    def propagate(self, tool_name: str, tool_use_id: str, inputs: list[str]) -> TaintLevel:
        """Determine output taint based on input taint levels (sticky propagation)."""
        max_level = TaintLevel.TRUSTED
        for content in inputs:
            fp = _fingerprint(content)
            rec = self.get(fp)
            if rec and _level_order(rec.taint_level) > _level_order(max_level):
                max_level = rec.taint_level
        self._tool_chain.append((tool_name, tool_use_id, max_level))
        return max_level


def _fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _level_order(level: TaintLevel) -> int:
    return {
        TaintLevel.TRUSTED: 0,
        TaintLevel.AUDITED: 1,
        TaintLevel.UNKNOWN: 2,
        TaintLevel.TAINTED: 3,
    }[level]


def classify_content(
    content: str,
    source: str,
    boundary: CriticalityLevel,
    verification: VerificationResult | None,
    session_nonce: str,
    config: SecurityConfig,
) -> TaintRecord:
    """Determine taint level for content based on its source and verification status."""
    fp = _fingerprint(content)

    # Nonce exfiltration — highest priority regardless of other factors
    if session_nonce and session_nonce in content:
        log.warning("NONCE EXFILTRATION DETECTED in content from %s", source)
        return TaintRecord(
            content_fingerprint=fp,
            taint_level=TaintLevel.TAINTED,
            source=source,
            acquired_at=_now(),
            tag="[CRITICAL-DATA: NONCE DETECTED]",
        )

    if boundary == CriticalityLevel.PERMISSIVE:
        level = TaintLevel.TRUSTED
        tag = None
    elif verification and verification.trusted:
        level = TaintLevel.TRUSTED
        tag = "[TRUSTED]"
    elif boundary == CriticalityLevel.AUDITED:
        level = TaintLevel.AUDITED
        tag = "[DATA]"
    else:
        # CRITICAL boundary with unverified content
        level = TaintLevel.TAINTED
        tag = "[CRITICAL-DATA]"

    rule = config.rule_for(boundary)
    if rule.tag and level != TaintLevel.TRUSTED:
        tag = rule.tag

    return TaintRecord(
        content_fingerprint=fp,
        taint_level=level,
        source=source,
        acquired_at=_now(),
        tag=tag,
    )
