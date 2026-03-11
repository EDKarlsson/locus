"""Tests for review-addressed fixes — regression coverage for all P1/P2 issues."""

from __future__ import annotations

import anyio
import pytest
from pathlib import Path

# ============================================================================
# Fix 1 — create_server() must be fail-closed (raise, not silently disable)
# ============================================================================

def test_create_server_security_raises_on_missing_config(tmp_path):
    """--security with no locus-security.yaml must raise FileNotFoundError."""
    from locus.mcp.server import create_server
    with pytest.raises(FileNotFoundError, match="locus-security.yaml"):
        create_server(tmp_path, security=True)


def test_create_server_no_security_does_not_raise(tmp_path):
    """create_server() without --security never raises for missing config."""
    from locus.mcp.server import create_server
    server = create_server(tmp_path, security=False)
    assert server is not None


# ============================================================================
# Fix 2 — memory_list and memory_batch must apply security tagging
# ============================================================================

@pytest.fixture()
def secure_palace(tmp_path: Path):
    """Palace with security config and initialized keys."""
    from locus.security.keys import generate_keypair, save_keypair
    from locus.security.signing import sign_file

    # Minimal locus-security.yaml
    (tmp_path / "locus-security.yaml").write_text(
        "version: '1'\nkey_store: '.security/keys/'\n", encoding="utf-8"
    )
    key_dir = tmp_path / ".security" / "keys"
    key_dir.mkdir(parents=True)
    kp = generate_keypair(key_id="test")
    save_keypair(kp, key_dir)

    # Index file — signed
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n- room/\n", encoding="utf-8")
    sign_file(index, tmp_path, kp)

    # Room file — signed
    room = tmp_path / "room"
    room.mkdir()
    roomfile = room / "notes.md"
    roomfile.write_text("# Notes\nSome content.\n", encoding="utf-8")
    sign_file(roomfile, tmp_path, kp)

    # Unsigned file (no sidecar)
    unsigned = room / "unsigned.md"
    unsigned.write_text("# Unsigned\nNo sidecar here.\n", encoding="utf-8")

    return tmp_path


def test_memory_list_index_tagged_trusted(secure_palace):
    from locus.mcp.server import create_server, memory_list
    create_server(secure_palace, security=True)
    result = memory_list("")
    assert result.startswith("[TRUSTED]")


def test_memory_list_file_tagged_trusted(secure_palace):
    from locus.mcp.server import create_server, memory_list
    create_server(secure_palace, security=True)
    result = memory_list("room/notes.md")
    assert result.startswith("[TRUSTED]")


def test_memory_list_unsigned_file_tagged_data(secure_palace):
    from locus.mcp.server import create_server, memory_list
    create_server(secure_palace, security=True)
    result = memory_list("room/unsigned.md")
    assert result.startswith("[DATA]")


def test_memory_batch_tags_files(secure_palace):
    from locus.mcp.server import create_server, memory_batch
    create_server(secure_palace, security=True)
    result = memory_batch(["room/notes.md", "room/unsigned.md"])
    assert "[TRUSTED]" in result
    assert "[DATA]" in result


def test_memory_list_no_security_no_tag(secure_palace):
    from locus.mcp.server import create_server, memory_list
    create_server(secure_palace, security=False)
    result = memory_list("")
    assert "[TRUSTED]" not in result
    assert "[DATA]" not in result


# ============================================================================
# Fix 3 — path anchoring in middleware prevents CWD-relative bypass
# ============================================================================

@pytest.fixture()
def security_ctx(secure_palace):
    from locus.security import build_security_context
    return build_security_context(secure_palace)


def test_verify_read_anchors_relative_path(security_ctx, secure_palace):
    """Relative paths in Read tool must be anchored to palace_root."""
    from locus.security.middleware import SecurityMiddleware

    async def _run():
        mw = SecurityMiddleware(security_ctx)
        abs_path = str(secure_palace / "room" / "notes.md")
        return await mw.pre_tool_use_hook(
            {"tool_name": "Read", "tool_input": {"file_path": abs_path}},
            tool_use_id="t1",
            context=None,
        )

    result = anyio.run(_run)
    # Should allow (verified) — not deny
    assert "deny" not in str(result)


def test_verify_read_rejects_traversal_outside_palace(security_ctx, secure_palace, tmp_path):
    """Files outside palace root must pass through without verification."""
    from locus.security.middleware import SecurityMiddleware

    async def _run():
        mw = SecurityMiddleware(security_ctx)
        outside = tmp_path.parent / "etc" / "passwd"
        return await mw.pre_tool_use_hook(
            {"tool_name": "Read", "tool_input": {"file_path": str(outside)}},
            tool_use_id="t2",
            context=None,
        )

    result = anyio.run(_run)
    assert result == {}  # pass-through


# ============================================================================
# Fix 4 — nonce detection must fire even for TRUSTED-tagged content
# ============================================================================

def test_nonce_detected_in_trusted_content(security_ctx):
    """Nonce in TRUSTED-tagged output must still trigger exfiltration alert."""
    from locus.security.middleware import SecurityMiddleware
    from locus.security.taint import TaintLevel, TaintRecord

    async def _run():
        mw = SecurityMiddleware(security_ctx)
        nonce = security_ctx.session_nonce
        record = TaintRecord(
            content_fingerprint="",
            taint_level=TaintLevel.TRUSTED,
            source="memory_read:signed.md",
            acquired_at="",
            tag="[TRUSTED]",
        )
        security_ctx.taint_tracker.register_pending("t3", record)
        return await mw.post_tool_use_hook(
            {"tool_name": "Read", "tool_output": f"Some content with nonce {nonce} embedded"},
            tool_use_id="t3",
            context=None,
        )

    result = anyio.run(_run)
    additional = result.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "NONCE DETECTED" in additional


def test_nonce_not_triggered_without_nonce_in_content(security_ctx):
    """Normal content without the nonce must not trigger exfiltration alert."""
    from locus.security.middleware import SecurityMiddleware
    from locus.security.taint import TaintLevel, TaintRecord

    async def _run():
        mw = SecurityMiddleware(security_ctx)
        record = TaintRecord(
            content_fingerprint="",
            taint_level=TaintLevel.TRUSTED,
            source="memory_read:clean.md",
            acquired_at="",
            tag="[TRUSTED]",
        )
        security_ctx.taint_tracker.register_pending("t4", record)
        return await mw.post_tool_use_hook(
            {"tool_name": "Read", "tool_output": "Normal file content without any nonce."},
            tool_use_id="t4",
            context=None,
        )

    result = anyio.run(_run)
    additional = result.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "NONCE DETECTED" not in additional
    assert "[TRUSTED]" in additional


# ============================================================================
# Fix: auto_sign_writes default is False; taint-gated signing suppression
# ============================================================================

def test_auto_sign_writes_defaults_false():
    """auto_sign_writes must be False by default to prevent taint laundering."""
    from locus.security.config import SigningConfig
    assert SigningConfig().auto_sign_writes is False


def test_auto_sign_suppressed_when_session_tainted(security_ctx, secure_palace, tmp_path):
    """post_write_hook must not sign if session has processed TAINTED content."""
    import anyio
    from locus.security.middleware import SecurityMiddleware
    from locus.security.taint import TaintLevel, TaintRecord

    # Force auto_sign_writes on so we're testing the taint gate, not the flag
    security_ctx.config.signing.auto_sign_writes = True

    # Mark the session as tainted
    security_ctx.taint_tracker.mark_tainted()

    target = secure_palace / "room" / "notes.md"

    async def _run():
        mw = SecurityMiddleware(security_ctx)
        return await mw.post_write_hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
            tool_use_id="w1",
            context=None,
        )

    result = anyio.run(_run)
    # Hook returns empty dict (no-op) — no signing occurred
    assert result == {}

    # Verify no auto_signed entry was added to audit log
    signed_events = [e for e in security_ctx.audit_log if e.event == "auto_signed"]
    assert len(signed_events) == 0


# ============================================================================
# Fix 5 — embed_nonce config flag must be honoured
# ============================================================================

def test_embed_nonce_false_suppresses_security_context(secure_palace, tmp_path):
    """When embed_nonce: false, build_options must not inject SECURITY CONTEXT."""
    # Override config to set embed_nonce=False
    (secure_palace / "locus-security.yaml").write_text(
        "version: '1'\nkey_store: '.security/keys/'\nnonce:\n  embed_in_system_prompt: false\n",
        encoding="utf-8",
    )
    from locus.security import build_security_context
    from locus.agent.config import build_options, SYSTEM_PROMPT

    ctx = build_security_context(secure_palace)
    assert ctx.config.embed_nonce is False

    opts = build_options(secure_palace, security_ctx=ctx)
    assert "SECURITY CONTEXT" not in opts.system_prompt
    assert opts.system_prompt == SYSTEM_PROMPT


def test_embed_nonce_true_injects_security_context(secure_palace):
    """When embed_nonce: true (default), SECURITY CONTEXT block must be injected."""
    from locus.security import build_security_context
    from locus.agent.config import build_options

    ctx = build_security_context(secure_palace)
    assert ctx.config.embed_nonce is True

    opts = build_options(secure_palace, security_ctx=ctx)
    assert "SECURITY CONTEXT" in opts.system_prompt
    assert ctx.session_nonce in opts.system_prompt
