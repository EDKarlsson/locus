"""Ed25519 keypair generation, storage, and rotation for Locus signing."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

log = logging.getLogger("locus.security.keys")


@dataclass
class KeyPair:
    key_id: str
    private_key_bytes: bytes | None  # None for retired/public-only entries
    public_key_bytes: bytes
    created_at: str
    expires_at: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc).isoformat() > self.expires_at

    def public_key_pem(self) -> str:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        pub = load_der_public_key(self.public_key_bytes)
        return pub.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()


@dataclass
class KeyStore:
    active: KeyPair
    retired: list[KeyPair] = field(default_factory=list)
    store_path: Path | None = None

    def find_by_id(self, key_id: str) -> KeyPair | None:
        if self.active.key_id == key_id:
            return self.active
        for kp in self.retired:
            if kp.key_id == key_id:
                return kp
        return None


def _passphrase() -> bytes | None:
    """Read LOCUS_SIGNING_PASSPHRASE env var. Returns None if unset (unencrypted key)."""
    val = os.environ.get("LOCUS_SIGNING_PASSPHRASE")
    return val.encode() if val else None


def generate_keypair(
    key_id: str | None = None,
    expires_days: int | None = 365,
) -> KeyPair:
    """Generate a new Ed25519 keypair."""
    if key_id is None:
        key_id = f"locus-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    expires_at = None
    if expires_days is not None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=expires_days)
        ).isoformat(timespec="seconds")

    return KeyPair(
        key_id=key_id,
        private_key_bytes=private_bytes,
        public_key_bytes=public_bytes,
        created_at=created_at,
        expires_at=expires_at,
    )


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def save_keypair(keypair: KeyPair, store_path: Path) -> None:
    """Write keypair to store_path/active.pem (PKCS8) and active.pub (DER public).

    If LOCUS_SIGNING_PASSPHRASE is set, the private key PEM is encrypted with
    BestAvailableEncryption (AES-256-CBC). Otherwise it is stored unencrypted.
    The public key is always written as unencrypted DER.
    """
    passphrase = _passphrase()
    private_key = Ed25519PrivateKey.from_private_bytes(keypair.private_key_bytes)
    if passphrase:
        enc = serialization.BestAvailableEncryption(passphrase)
    else:
        enc = serialization.NoEncryption()

    # PKCS8 is the standard format for PEM-encoded private keys and supports
    # optional passphrase encryption via BestAvailableEncryption.
    pem_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        enc,
    )
    _atomic_write(store_path / "active.pem", pem_bytes)

    # Public key: DER, unencrypted
    _atomic_write(store_path / "active.pub", keypair.public_key_bytes)

    # Metadata
    meta = {
        "key_id": keypair.key_id,
        "created_at": keypair.created_at,
        "expires_at": keypair.expires_at,
    }
    _atomic_write(store_path / "active.json", json.dumps(meta, indent=2).encode())
    log.info("saved keypair %s to %s", keypair.key_id, store_path)


def load_keystore(store_path: Path) -> KeyStore:
    """Load the active keypair and any retired public keys from store_path."""
    active_pem = store_path / "active.pem"
    active_pub = store_path / "active.pub"
    active_meta = store_path / "active.json"

    if not active_pem.exists() or not active_pub.exists():
        raise FileNotFoundError(
            f"No active keypair found in {store_path}. "
            "Run: locus-security init-keys --palace <path>"
        )

    passphrase = _passphrase()
    private_key = serialization.load_pem_private_key(
        active_pem.read_bytes(), password=passphrase
    )
    private_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = active_pub.read_bytes()

    meta: dict = {}
    if active_meta.exists():
        meta = json.loads(active_meta.read_text())

    active = KeyPair(
        key_id=meta.get("key_id", "unknown"),
        private_key_bytes=private_bytes,
        public_key_bytes=public_bytes,
        created_at=meta.get("created_at", ""),
        expires_at=meta.get("expires_at"),
    )

    # Load retired public keys
    retired: list[KeyPair] = []
    retired_dir = store_path / "retired"
    if retired_dir.is_dir():
        for pub_file in sorted(retired_dir.glob("*.pub")):
            meta_file = pub_file.with_suffix(".json")
            ret_meta: dict = {}
            if meta_file.exists():
                ret_meta = json.loads(meta_file.read_text())
            retired.append(
                KeyPair(
                    key_id=ret_meta.get("key_id", pub_file.stem),
                    private_key_bytes=None,
                    public_key_bytes=pub_file.read_bytes(),
                    created_at=ret_meta.get("created_at", ""),
                    expires_at=ret_meta.get("expires_at"),
                )
            )

    return KeyStore(active=active, retired=retired, store_path=store_path)


def rotate_keypair(store: KeyStore, store_path: Path) -> KeyPair:
    """Retire the current active key and generate a new one."""
    retired_dir = store_path / "retired"
    retired_dir.mkdir(parents=True, exist_ok=True)

    # Archive current public key and metadata only (never retain private key after rotation)
    _atomic_write(
        retired_dir / f"{store.active.key_id}.pub",
        store.active.public_key_bytes,
    )
    meta = {
        "key_id": store.active.key_id,
        "created_at": store.active.created_at,
        "expires_at": store.active.expires_at,
    }
    _atomic_write(
        retired_dir / f"{store.active.key_id}.json",
        json.dumps(meta, indent=2).encode(),
    )

    new_keypair = generate_keypair()
    save_keypair(new_keypair, store_path)
    log.info("rotated key: %s → %s", store.active.key_id, new_keypair.key_id)
    return new_keypair
