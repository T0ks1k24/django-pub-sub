"""Validation helpers for user input and RSA public keys."""

from __future__ import annotations

import re
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,150}$")
_PUBLIC_KEY_PATTERN = re.compile(
    r"^-----BEGIN PUBLIC KEY-----\n(?:[A-Za-z0-9+/=]+\n)+-----END PUBLIC KEY-----\n?$"
)


def sanitize(value: str, *, max_length: int = 8192) -> str:
    """Strip and validate a generic text input."""
    if not isinstance(value, str):
        raise ValueError("Value must be a string.")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Value cannot be empty.")
    if len(cleaned) > max_length:
        raise ValueError("Value is too long.")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in cleaned):
        raise ValueError("Value contains control characters.")
    return cleaned


def validate_public_key(key: str) -> None:
    """Validate that a string contains a PEM-encoded RSA public key."""
    normalized = sanitize(key).replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized = f"{normalized}\n"
    if not _PUBLIC_KEY_PATTERN.fullmatch(normalized):
        raise ValueError("Malformed PEM public key.")

    loaded_key = serialization.load_pem_public_key(normalized.encode("utf-8"))
    if not isinstance(loaded_key, rsa.RSAPublicKey):
        raise ValueError("Public key must be RSA.")
    if loaded_key.key_size < 2048:
        raise ValueError("RSA key size must be at least 2048 bits.")


def validate_username(username: Any) -> str:
    """Validate and normalize a username used in authentication flows."""
    cleaned = sanitize(username)
    if not _USERNAME_PATTERN.fullmatch(cleaned):
        raise ValueError("Username contains unsupported characters.")
    return cleaned
