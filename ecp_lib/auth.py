"""Authentication helpers built around Django auth plus ECP key checks."""

from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth import authenticate

from .crypto import generate_keys, sign, verify
from .models import ECPKey
from .validators import sanitize, validate_public_key, validate_username


def create_user_keys(user: Any) -> str:
    """Generate a fresh key pair for a user and persist the public key."""
    private_key, public_key = generate_keys()
    validate_public_key(public_key)

    ECPKey.objects.update_or_create(  # pylint: disable=no-member
        user=user,
        defaults={"public_key": public_key},
    )
    return private_key


def create_challenge() -> str:
    """Return a one-time challenge used during ECP authentication."""
    return f"login-test:{secrets.token_urlsafe(16)}"


def read_private_key(file: Any) -> str:
    """Read a PEM private key from an uploaded Django file object."""
    if file is None:
        raise ValueError("Private key file is required.")

    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    if not isinstance(content, str):
        raise ValueError("Invalid private key file.")

    return sanitize(content)


def authenticate_with_private_key(
    request: Any,
    username: str,
    password: str,
    private_key: str,
) -> tuple[Any | None, str | None]:
    """Authenticate a user with Django credentials and an RSA private key."""
    user = None
    error = None
    public_key = None
    challenge = None
    signature = None

    try:
        username = validate_username(username)
        password = sanitize(password)
        private_key = sanitize(private_key)
    except ValueError as exc:
        error = str(exc)

    if error is None:
        user = authenticate(request=request, username=username, password=password)
        if user is None:
            error = "Invalid username or password."

    if error is None:
        public_key = getattr(getattr(user, "ecp_key", None), "public_key", None)
        if not isinstance(public_key, str):
            error = "Public key not found for user."

    if error is None:
        try:
            validate_public_key(public_key)
        except ValueError as exc:
            error = str(exc)

    if error is None:
        challenge = create_challenge()
        try:
            signature = sign(private_key, challenge)
        except ValueError as exc:
            error = str(exc)

    if error is None and not verify(public_key, challenge, signature):
        error = "Private key does not match stored public key."

    return user if error is None else None, error
