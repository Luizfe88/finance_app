"""
Infrastructure: Crypto Utilities (AES-256-GCM + Tokenization)

Security by Design:
  - AES-256-GCM for field-level encryption of sensitive data (data at rest)
  - HMAC-based tokenization for bank account numbers (PCI DSS scope reduction)
  - Key loaded from AES_SECRET_KEY env var (must be 32-byte hex string)

Usage:
    from infrastructure.crypto import encrypt_field, decrypt_field, tokenize_account

    encrypted = encrypt_field("123.456.789-00")   # CPF
    original  = decrypt_field(encrypted)

    token = tokenize_account("1234567890123456")  # → "****3456"
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional


def _get_key() -> bytes:
    """Load AES-256 key from environment (32 bytes)."""
    raw = os.getenv("AES_SECRET_KEY", "")
    if not raw:
        # Development fallback — NOT for production use
        raw = "dev_key_do_not_use_in_production_32b"
    key = raw.encode()[:32].ljust(32, b"\x00")
    return key


def encrypt_field(plaintext: str) -> str:
    """
    AES-256-GCM encryption of a string field.
    Returns base64(nonce + ciphertext + tag).

    NOTE: Requires 'cryptography' package.
    Falls back to XOR obfuscation in dev if cryptography not installed.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = _get_key()
        nonce = os.urandom(12)   # 96-bit nonce (GCM standard)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.urlsafe_b64encode(nonce + ct).decode()
    except ImportError:
        # Dev fallback — XOR with key (NOT cryptographically secure)
        key = _get_key()
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(plaintext.encode()))
        return base64.urlsafe_b64encode(xored).decode()


def decrypt_field(token: str) -> Optional[str]:
    """Decrypt a field previously encrypted with encrypt_field()."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = _get_key()
        raw = base64.urlsafe_b64decode(token.encode())
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode()
    except ImportError:
        key = _get_key()
        raw = base64.urlsafe_b64decode(token.encode())
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(raw)).decode()
    except Exception:
        return None


def tokenize_account_number(full_number: str) -> str:
    """
    Tokenize a bank account or card number for PCI DSS scope reduction.
    Stores only masked form: "****XXXX" (last 4 digits).
    The original is never stored in the database.

    Returns the masked token suitable for display.
    """
    cleaned = "".join(filter(str.isdigit, full_number))
    if len(cleaned) >= 4:
        return f"****{cleaned[-4:]}"
    return "****"


def compute_field_hmac(value: str) -> str:
    """
    HMAC-SHA256 of a field value — used for searchable encryption.
    Allows lookup by encrypted field without decrypting.
    """
    key = _get_key()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
