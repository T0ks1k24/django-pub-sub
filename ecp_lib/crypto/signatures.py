from __future__ import annotations

import base64
import binascii

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from ..core.exceptions import KeyValidationError


def sign_payload(private_key_pem: str, payload: str | bytes) -> str:
    """Create a base64-encoded RSA-PSS signature for the provided payload."""
    private_key = _load_private_rsa_key(private_key_pem)
    payload_bytes = _as_bytes(payload)

    signature = private_key.sign(
        payload_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify_signature(public_key_pem: str, payload: str | bytes, signature: str) -> bool:
    """Verify a base64-encoded RSA-PSS signature against the provided payload."""
    public_key = _load_public_rsa_key(public_key_pem)
    payload_bytes = _as_bytes(payload)

    try:
        signature_bytes = base64.b64decode(signature.encode("ascii"), validate=True)
    except (binascii.Error, ValueError):
        return False

    try:
        public_key.verify(
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


def _as_bytes(payload: str | bytes) -> bytes:
    if isinstance(payload, bytes):
        return payload
    return payload.encode("utf-8")
