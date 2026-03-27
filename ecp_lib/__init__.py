"""Public package exports for the ECP library."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import (
        authenticate_with_private_key,
        create_challenge,
        create_user_keys,
        read_private_key,
    )
    from .crypto import generate_keys, sign, verify
    from .middleware import ECPMiddleware
    from .models import ECPKey
    from .validators import sanitize, validate_public_key

__all__ = [
    "authenticate_with_private_key",
    "create_challenge",
    "create_user_keys",
    "ECPKey",
    "ECPMiddleware",
    "generate_keys",
    "read_private_key",
    "sanitize",
    "sign",
    "validate_public_key",
    "verify",
]

_EXPORTS = {
    "authenticate_with_private_key": ("ecp_lib.auth", "authenticate_with_private_key"),
    "create_challenge": ("ecp_lib.auth", "create_challenge"),
    "create_user_keys": ("ecp_lib.auth", "create_user_keys"),
    "ECPKey": ("ecp_lib.models", "ECPKey"),
    "ECPMiddleware": ("ecp_lib.middleware", "ECPMiddleware"),
    "generate_keys": ("ecp_lib.crypto", "generate_keys"),
    "read_private_key": ("ecp_lib.auth", "read_private_key"),
    "sanitize": ("ecp_lib.validators", "sanitize"),
    "sign": ("ecp_lib.crypto", "sign"),
    "validate_public_key": ("ecp_lib.validators", "validate_public_key"),
    "verify": ("ecp_lib.crypto", "verify"),
}


def __getattr__(name: str):
    """Lazily resolve public exports to avoid early Django model imports."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
