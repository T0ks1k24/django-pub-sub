from __future__ import annotations

from importlib import import_module

__all__ = [
    "AuthenticationChallenge",
    "AttachUserPublicKeyMiddleware",
    "ECPAuthenticationBackend",
    "issue_authentication_challenge",
    "verify_authentication_response",
]

_EXPORTS = {
    "AuthenticationChallenge": ("ecp_lib.auth.challenges", "AuthenticationChallenge"),
    "AttachUserPublicKeyMiddleware": ("ecp_lib.auth.middleware", "AttachUserPublicKeyMiddleware"),
    "ECPAuthenticationBackend": ("ecp_lib.auth.backend", "ECPAuthenticationBackend"),
    "issue_authentication_challenge": ("ecp_lib.auth.challenges", "issue_authentication_challenge"),
    "verify_authentication_response": ("ecp_lib.auth.challenges", "verify_authentication_response"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
