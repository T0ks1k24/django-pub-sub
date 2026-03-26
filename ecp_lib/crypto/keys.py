from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..core.exceptions import KeyValidationError


def generate_rsa_key_pair(*, key_size: int = 2048) -> tuple[str, str]:
    """Generate RSA keypair and return (private_pem, public_pem)."""
    _validate_key_size(key_size)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    validate_rsa_keys(private_key_pem, public_key_pem)
    return private_key_pem, public_key_pem


def validate_rsa_keys(private_key_pem: str, public_key_pem: str) -> bool:
    """Validate that private/public PEM keys belong to the same RSA keypair."""
    private_key = _load_private_rsa_key(private_key_pem)
    public_key = _load_public_rsa_key(public_key_pem)

    if private_key.key_size < 2048 or public_key.key_size < 2048:
        raise KeyValidationError(
            "RSA key size must be at least 2048 bits",
            private_key_size=private_key.key_size,
            public_key_size=public_key.key_size,
        )

    numbers_private = private_key.private_numbers().public_numbers
    numbers_public = public_key.public_numbers()

    if numbers_private.n != numbers_public.n or numbers_private.e != numbers_public.e:
        raise KeyValidationError("Private and public keys do not form a valid pair")

    return True


def generating_rsa_keys() -> str:
    """Backward-compatible wrapper with previous output format."""
    private_key_pem, public_key_pem = generate_rsa_key_pair()
    return f"Private:\n{private_key_pem}\nPublic:\n{public_key_pem}"


def _validate_key_size(key_size: int) -> None:
    if key_size < 2048:
        raise KeyValidationError("RSA key size must be at least 2048 bits", key_size=key_size)
    if key_size % 256 != 0:
        raise KeyValidationError(
            "RSA key size must be a multiple of 256 bits",
            key_size=key_size,
        )


def _load_private_rsa_key(private_key_pem: str) -> rsa.RSAPrivateKey:
    if not isinstance(private_key_pem, str) or not private_key_pem.strip():
        raise KeyValidationError("Private key PEM must be a non-empty string")

    try:
        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    except ValueError as exc:
        raise KeyValidationError("Private key PEM is invalid") from exc

    if not isinstance(key, rsa.RSAPrivateKey):
        raise KeyValidationError("Private key must be RSA")

    return key


def _load_public_rsa_key(public_key_pem: str) -> rsa.RSAPublicKey:
    if not isinstance(public_key_pem, str) or not public_key_pem.strip():
        raise KeyValidationError("Public key PEM must be a non-empty string")

    try:
        key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    except ValueError as exc:
        raise KeyValidationError("Public key PEM is invalid") from exc

    if not isinstance(key, rsa.RSAPublicKey):
        raise KeyValidationError("Public key must be RSA")

    return key
