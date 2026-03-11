"""Tests for locus.security.signing — Ed25519 sign/verify, tamper detection."""

import pytest
from pathlib import Path

from locus.security.keys import generate_keypair, KeyStore
from locus.security.signing import sign_file, verify_file, sign_system_prompt, _sidecar_path


@pytest.fixture()
def palace(tmp_path: Path) -> Path:
    (tmp_path / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    room = tmp_path / "global" / "networking"
    room.mkdir(parents=True)
    (room / "networking.md").write_text("# Networking\nSome facts.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def keypair():
    return generate_keypair(key_id="test-key")


@pytest.fixture()
def keystore(keypair):
    return KeyStore(active=keypair)


def test_sign_creates_sidecar(palace, keypair):
    target = palace / "global" / "networking" / "networking.md"
    sig = sign_file(target, palace, keypair)
    sidecar = _sidecar_path(target)
    assert sidecar.exists()
    assert sig.protocol == "locus-sig-v1"
    assert sig.key_id == "test-key"


def test_verify_valid_signature(palace, keypair, keystore):
    target = palace / "global" / "networking" / "networking.md"
    sign_file(target, palace, keypair)
    result = verify_file(target, palace, keystore)
    assert result.trusted is True
    assert result.reason == "signature valid"
    assert result.key_id == "test-key"


def test_verify_missing_sidecar(palace, keystore):
    target = palace / "global" / "networking" / "networking.md"
    result = verify_file(target, palace, keystore)
    assert result.trusted is False
    assert result.reason == "no sidecar"


def test_verify_content_tampered(palace, keypair, keystore):
    target = palace / "global" / "networking" / "networking.md"
    sign_file(target, palace, keypair)
    # Tamper with the content after signing
    target.write_text("# Networking\nMalicious content injected here!\n", encoding="utf-8")
    result = verify_file(target, palace, keystore)
    assert result.trusted is False
    assert result.reason == "content tampered"


def test_verify_unknown_key(palace, keypair):
    target = palace / "global" / "networking" / "networking.md"
    sign_file(target, palace, keypair)
    # Keystore with a different key — won't find "test-key"
    other_keypair = generate_keypair(key_id="other-key")
    other_store = KeyStore(active=other_keypair)
    result = verify_file(target, palace, other_store)
    assert result.trusted is False
    assert "key not found" in result.reason


def test_verify_retired_key_still_works(palace, keypair):
    target = palace / "global" / "networking" / "networking.md"
    sign_file(target, palace, keypair)

    # Create a new active key, retire the old one
    from locus.security.keys import KeyPair
    new_kp = generate_keypair(key_id="new-key")
    store_with_retired = KeyStore(
        active=new_kp,
        retired=[keypair],
    )
    result = verify_file(target, palace, store_with_retired)
    assert result.trusted is True


def test_sign_system_prompt(keypair):
    sig_b64, key_id = sign_system_prompt("You are a Locus agent.", keypair, nonce="abc123")
    assert key_id == "test-key"
    assert len(sig_b64) > 0


def test_sign_retired_key_raises(keypair):
    from locus.security.keys import KeyPair
    retired = KeyPair(
        key_id="retired",
        private_key_bytes=None,  # no private key
        public_key_bytes=keypair.public_key_bytes,
        created_at="",
    )
    with pytest.raises(ValueError, match="no private key"):
        sign_system_prompt("prompt", retired, nonce="x")
