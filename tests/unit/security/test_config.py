"""Tests for locus.security.config — YAML parsing and defaults."""

import pytest
from pathlib import Path

from locus.security.config import (
    CriticalityLevel,
    load_security_config,
    SecurityConfig,
)


@pytest.fixture()
def palace(tmp_path: Path) -> Path:
    (tmp_path / "INDEX.md").write_text("# Index\n")
    return tmp_path


def test_load_returns_none_when_missing(palace):
    result = load_security_config(palace)
    assert result is None


def test_load_parses_minimal_config(palace):
    (palace / "locus-security.yaml").write_text(
        "version: '1'\nkey_store: '.security/keys/'\n"
    )
    config = load_security_config(palace)
    assert config is not None
    assert config.version == "1"
    assert config.boundaries.memory_read == CriticalityLevel.AUDITED
    assert config.boundaries.external_data == CriticalityLevel.CRITICAL


def test_load_parses_boundary_overrides(palace):
    (palace / "locus-security.yaml").write_text(
        "version: '1'\nboundaries:\n  memory_read: CRITICAL\n  user_input: AUDITED\n"
    )
    config = load_security_config(palace)
    assert config.boundaries.memory_read == CriticalityLevel.CRITICAL
    assert config.boundaries.user_input == CriticalityLevel.AUDITED


def test_load_parses_signing_config(palace):
    (palace / "locus-security.yaml").write_text(
        "version: '1'\nsigning:\n  auto_sign_writes: false\n  allow_unsigned_reads: true\n"
    )
    config = load_security_config(palace)
    assert config.signing.auto_sign_writes is False
    assert config.signing.allow_unsigned_reads is True


def test_rule_for(palace):
    (palace / "locus-security.yaml").write_text("version: '1'\n")
    config = load_security_config(palace)
    critical_rule = config.rule_for(CriticalityLevel.CRITICAL)
    assert critical_rule.block is True
    assert critical_rule.tag == "[CRITICAL-DATA]"

    audited_rule = config.rule_for(CriticalityLevel.AUDITED)
    assert audited_rule.block is False
    assert audited_rule.flag_to_agent is True


def test_boundary_for(palace):
    (palace / "locus-security.yaml").write_text("version: '1'\n")
    config = load_security_config(palace)
    assert config.boundary_for("memory_write") == CriticalityLevel.CRITICAL
    assert config.boundary_for("user_input") == CriticalityLevel.PERMISSIVE
    assert config.boundary_for("unknown_boundary") == CriticalityLevel.AUDITED
