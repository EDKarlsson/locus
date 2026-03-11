"""Tests for locus.security.keys — keypair generation, save/load, rotation."""

import pytest
from pathlib import Path

from locus.security.keys import generate_keypair, save_keypair, load_keystore, rotate_keypair


def test_generate_keypair_defaults():
    kp = generate_keypair()
    assert kp.key_id.startswith("locus-")
    assert len(kp.private_key_bytes) == 32
    assert len(kp.public_key_bytes) > 0
    assert kp.expires_at is not None


def test_generate_keypair_no_expiry():
    kp = generate_keypair(expires_days=None)
    assert kp.expires_at is None


def test_generate_keypair_custom_id():
    kp = generate_keypair(key_id="test-key-001")
    assert kp.key_id == "test-key-001"


def test_keypair_public_key_pem(tmp_path):
    kp = generate_keypair()
    pem = kp.public_key_pem()
    assert "BEGIN PUBLIC KEY" in pem


def test_save_and_load_roundtrip(tmp_path):
    kp = generate_keypair(key_id="roundtrip-test")
    save_keypair(kp, tmp_path)

    store = load_keystore(tmp_path)
    assert store.active.key_id == "roundtrip-test"
    assert store.active.private_key_bytes == kp.private_key_bytes
    assert store.active.public_key_bytes == kp.public_key_bytes
    assert store.retired == []


def test_load_missing_keys_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_keystore(tmp_path)


def test_rotation_creates_retired(tmp_path):
    kp1 = generate_keypair(key_id="key-v1")
    save_keypair(kp1, tmp_path)
    store = load_keystore(tmp_path)

    new_kp = rotate_keypair(store, tmp_path)

    # Original public key archived to retired/
    assert (tmp_path / "retired" / "key-v1.pub").exists()
    # Private key is NOT retained for retired key
    assert not (tmp_path / "retired" / "key-v1.pem").exists()

    # New active key loaded correctly
    new_store = load_keystore(tmp_path)
    assert new_store.active.key_id == new_kp.key_id
    assert len(new_store.retired) == 1
    assert new_store.retired[0].key_id == "key-v1"
    assert new_store.retired[0].private_key_bytes is None  # public-only


def test_keystore_find_by_id(tmp_path):
    kp1 = generate_keypair(key_id="key-v1")
    save_keypair(kp1, tmp_path)
    store = load_keystore(tmp_path)
    rotate_keypair(store, tmp_path)
    store2 = load_keystore(tmp_path)

    assert store2.find_by_id("key-v1") is not None
    assert store2.find_by_id("nonexistent") is None
