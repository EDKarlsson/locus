"""Tests for locus.security.nonce — generation uniqueness and injection."""

from locus.security.nonce import generate_session_nonce, inject_security_context
from locus.security.keys import generate_keypair


def test_nonce_is_32_chars():
    nonce = generate_session_nonce("test-palace")
    assert len(nonce) == 32


def test_nonces_are_unique():
    nonces = {generate_session_nonce("palace") for _ in range(50)}
    assert len(nonces) == 50


def test_nonce_is_url_safe():
    nonce = generate_session_nonce("palace")
    # base64url chars only
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in nonce)


def test_inject_security_context_includes_nonce():
    keypair = generate_keypair(key_id="test")
    base = "You are a Locus agent."
    nonce = generate_session_nonce("palace")

    result = inject_security_context(base, nonce=nonce, keypair=keypair, palace_slug="palace")

    assert nonce in result
    assert "SECURITY CONTEXT" in result
    assert "SECURITY RULES" in result


def test_inject_includes_public_key():
    keypair = generate_keypair(key_id="test")
    nonce = generate_session_nonce("p")
    result = inject_security_context("Base prompt.", nonce=nonce, keypair=keypair, palace_slug="p")
    assert "BEGIN PUBLIC KEY" in result


def test_inject_includes_signature():
    keypair = generate_keypair(key_id="test")
    nonce = generate_session_nonce("p")
    result = inject_security_context("Base prompt.", nonce=nonce, keypair=keypair, palace_slug="p")
    assert "System prompt signature:" in result
