from __future__ import annotations

import re
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Username пропускаємо тільки через whitelist.
# Це простий спосіб відсікти сміття і частину інʼєкційних payload-ів.
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,150}$")

# Підпис очікується як base64-рядок.
_SIGNATURE_PATTERN = re.compile(r"^[A-Za-z0-9+/=]{1,8192}$")

# Public key має бути саме в PEM-форматі.
_PUBLIC_KEY_PATTERN = re.compile(
    r"^-----BEGIN PUBLIC KEY-----\n(?:[A-Za-z0-9+/=]+\n)+-----END PUBLIC KEY-----\n?$"
)


def sanitize(value: str) -> str:
    # Базова санітизація для вхідних значень:
    # прибираємо зайві пробіли і блокуємо явно підозрілі значення.
    if not isinstance(value, str):
        raise ValueError("Value must be a string.")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Value cannot be empty.")
    if len(cleaned) > 8192:
        raise ValueError("Value is too long.")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in cleaned):
        raise ValueError("Value contains control characters.")
    return cleaned


def validate_public_key(key: str) -> None:
    # Перевіряємо і синтаксис PEM, і реальну структуру RSA public key.
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
    # Окрема валідація username потрібна для безпечного пошуку користувача в БД.
    cleaned = sanitize(username)
    if not _USERNAME_PATTERN.fullmatch(cleaned):
        raise ValueError("Username contains unsupported characters.")
    return cleaned


def validate_signature(signature: str) -> str:
    # На цьому рівні лише перевіряємо форму підпису.
    # Сама криптографічна перевірка відбувається в crypto.verify().
    cleaned = sanitize(signature)
    if not _SIGNATURE_PATTERN.fullmatch(cleaned):
        raise ValueError("Signature format is invalid.")
    return cleaned
