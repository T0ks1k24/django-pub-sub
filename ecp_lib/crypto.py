"""RSA key generation and signing helpers used by the ECP flows."""

from __future__ import annotations

import base64
import binascii

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

MIN_RSA_KEY_SIZE = 2048


def generate_keys(*, key_size: int = MIN_RSA_KEY_SIZE) -> tuple[str, str]:
    """Generate a new RSA private/public key pair in PEM format."""
    if key_size < MIN_RSA_KEY_SIZE:
        raise ValueError(f"RSA key size must be at least {MIN_RSA_KEY_SIZE} bits.")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def sign(private_key: str, payload: str) -> str:
    """Sign a text payload with a PEM-encoded RSA private key."""
    key = _load_private_key(private_key)
    payload_bytes = _to_bytes(payload)
    signature = key.sign(
        payload_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify(public_key: str, payload: str, signature: str) -> bool:
    """Verify a base64-encoded signature against a payload and public key."""
    key = _load_public_key(public_key)
    payload_bytes = _to_bytes(payload)

    try:
        signature_bytes = base64.b64decode(signature.encode("ascii"), validate=True)
    except (ValueError, binascii.Error):
        return False

    try:
        key.verify(
            signature_bytes,
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return False

    return True


def _load_private_key(private_key: str) -> rsa.RSAPrivateKey:
    if not isinstance(private_key, str) or not private_key.strip():
        raise ValueError("Private key must be a non-empty PEM string.")

    try:
        key = serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)
    except ValueError as exc:
        raise ValueError("Invalid private key PEM.") from exc

    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < MIN_RSA_KEY_SIZE:
        raise ValueError("Private key must be RSA and at least 2048 bits.")

    return key


def _load_public_key(public_key: str) -> rsa.RSAPublicKey:
    if not isinstance(public_key, str) or not public_key.strip():
        raise ValueError("Public key must be a non-empty PEM string.")

    try:
        key = serialization.load_pem_public_key(public_key.encode("utf-8"))
    except ValueError as exc:
        raise ValueError("Invalid public key PEM.") from exc

    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < MIN_RSA_KEY_SIZE:
        raise ValueError("Public key must be RSA and at least 2048 bits.")

    return key


def _to_bytes(payload: str | bytes) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if not isinstance(payload, str):
        raise ValueError("Payload must be str or bytes.")
    return payload.encode("utf-8")
