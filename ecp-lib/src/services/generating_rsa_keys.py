from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .validate_rsa_keys import validate_rsa_keys


def generate_rsa_key_pair() -> tuple[str, str]:
    """Generate RSA keypair and return (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
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

    if not validate_rsa_keys(private_key_pem, public_key_pem):
        raise ValueError("Generated RSA key pair validation failed")

    return private_key_pem, public_key_pem


def generating_rsa_keys() -> str:
    """Backward-compatible wrapper with previous output format."""
    private_key_pem, public_key_pem = generate_rsa_key_pair()
    return f"Private:\n{private_key_pem}\nPublic:\n{public_key_pem}"


if __name__ == "__main__":
    generating_rsa_keys()

