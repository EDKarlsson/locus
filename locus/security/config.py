"""Security configuration for Locus — boundary criticality and enforcement rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class CriticalityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    AUDITED = "AUDITED"
    PERMISSIVE = "PERMISSIVE"


@dataclass
class EnforcementRule:
    block: bool
    log: bool
    tag: str | None
    flag_to_agent: bool = False


@dataclass
class BoundaryConfig:
    memory_read: CriticalityLevel = CriticalityLevel.AUDITED
    memory_write: CriticalityLevel = CriticalityLevel.CRITICAL
    tool_output: CriticalityLevel = CriticalityLevel.AUDITED
    user_input: CriticalityLevel = CriticalityLevel.PERMISSIVE
    external_data: CriticalityLevel = CriticalityLevel.CRITICAL
    mcp_tool_result: CriticalityLevel = CriticalityLevel.AUDITED


_DEFAULT_ENFORCEMENT: dict[CriticalityLevel, EnforcementRule] = {
    CriticalityLevel.CRITICAL: EnforcementRule(
        block=True, log=True, tag="[CRITICAL-DATA]"
    ),
    CriticalityLevel.AUDITED: EnforcementRule(
        block=False, log=True, tag="[DATA]", flag_to_agent=True
    ),
    CriticalityLevel.PERMISSIVE: EnforcementRule(
        block=False, log=False, tag=None
    ),
}


@dataclass
class SigningConfig:
    enabled: bool = True
    auto_sign_writes: bool = False  # Off by default — opt in explicitly. Auto-signing
    # can launder tainted content into the trusted tier if the agent has been
    # compromised mid-session. Enable only in tightly controlled pipelines.
    verify_on_read: bool = True
    allow_unsigned_reads: bool = False


@dataclass
class SecurityConfig:
    version: str
    key_store_path: Path
    boundaries: BoundaryConfig
    enforcement: dict[CriticalityLevel, EnforcementRule]
    signing: SigningConfig
    embed_nonce: bool = True

    def rule_for(self, level: CriticalityLevel) -> EnforcementRule:
        return self.enforcement[level]

    def boundary_for(self, boundary_name: str) -> CriticalityLevel:
        return getattr(self.boundaries, boundary_name, CriticalityLevel.AUDITED)


def _parse_criticality(value: Any) -> CriticalityLevel:
    try:
        return CriticalityLevel(str(value).upper())
    except ValueError:
        return CriticalityLevel.AUDITED


def _parse_enforcement(raw: dict[str, Any]) -> dict[CriticalityLevel, EnforcementRule]:
    result = dict(_DEFAULT_ENFORCEMENT)
    for level_str, rule_raw in raw.items():
        level = _parse_criticality(level_str)
        result[level] = EnforcementRule(
            block=bool(rule_raw.get("block", result[level].block)),
            log=bool(rule_raw.get("log", result[level].log)),
            tag=rule_raw.get("tag", result[level].tag),
            flag_to_agent=bool(rule_raw.get("flag_to_agent", result[level].flag_to_agent)),
        )
    return result


def load_security_config(palace_root: Path) -> SecurityConfig | None:
    """Load locus-security.yaml from palace root. Returns None if not found."""
    config_path = palace_root / "locus-security.yaml"
    if not config_path.exists():
        return None

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    key_store_rel = raw.get("key_store", ".security/keys/")
    key_store_path = (palace_root / key_store_rel).resolve()

    boundaries_raw = raw.get("boundaries", {})
    boundaries = BoundaryConfig(
        memory_read=_parse_criticality(boundaries_raw.get("memory_read", "AUDITED")),
        memory_write=_parse_criticality(boundaries_raw.get("memory_write", "CRITICAL")),
        tool_output=_parse_criticality(boundaries_raw.get("tool_output", "AUDITED")),
        user_input=_parse_criticality(boundaries_raw.get("user_input", "PERMISSIVE")),
        external_data=_parse_criticality(boundaries_raw.get("external_data", "CRITICAL")),
        mcp_tool_result=_parse_criticality(boundaries_raw.get("mcp_tool_result", "AUDITED")),
    )

    enforcement = _parse_enforcement(raw.get("enforcement", {}))

    signing_raw = raw.get("signing", {})
    signing = SigningConfig(
        enabled=bool(signing_raw.get("enabled", True)),
        auto_sign_writes=bool(signing_raw.get("auto_sign_writes", False)),
        verify_on_read=bool(signing_raw.get("verify_on_read", True)),
        allow_unsigned_reads=bool(signing_raw.get("allow_unsigned_reads", False)),
    )

    nonce_raw = raw.get("nonce", {})
    embed_nonce = bool(nonce_raw.get("embed_in_system_prompt", True))

    return SecurityConfig(
        version=str(raw.get("version", "1")),
        key_store_path=key_store_path,
        boundaries=boundaries,
        enforcement=enforcement,
        signing=signing,
        embed_nonce=embed_nonce,
    )
