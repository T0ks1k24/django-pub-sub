from __future__ import annotations

from importlib import import_module

__all__ = [
    "AuthenticationChallenge",
    "AttachUserPublicKeyMiddleware",
    "ChallengeValidationError",
    "ECPAuthenticationBackend",
    "ECPAuthenticationError",
    "ECPError",
    "ECPUserPublicKey",
    "KeyValidationError",
    "SignatureVerificationError",
    "ValidationError",
    "generate_rsa_key_pair",
    "generating_rsa_keys",
    "issue_authentication_challenge",
    "sign_payload",
    "validate_rsa_keys",
    "verify_authentication_response",
    "verify_signature",
]

_EXPORTS = {
    "AuthenticationChallenge": ("ecp_lib.auth.challenges", "AuthenticationChallenge"),
    "AttachUserPublicKeyMiddleware": ("ecp_lib.auth.middleware", "AttachUserPublicKeyMiddleware"),
    "ChallengeValidationError": ("ecp_lib.core.exceptions", "ChallengeValidationError"),
    "ECPAuthenticationBackend": ("ecp_lib.auth.backend", "ECPAuthenticationBackend"),
    "ECPAuthenticationError": ("ecp_lib.core.exceptions", "ECPAuthenticationError"),
    "ECPError": ("ecp_lib.core.exceptions", "ECPError"),
    "ECPUserPublicKey": ("ecp_lib.models", "ECPUserPublicKey"),
    "KeyValidationError": ("ecp_lib.core.exceptions", "KeyValidationError"),
    "SignatureVerificationError": ("ecp_lib.core.exceptions", "SignatureVerificationError"),
    "ValidationError": ("ecp_lib.core.exceptions", "ValidationError"),
    "generate_rsa_key_pair": ("ecp_lib.crypto", "generate_rsa_key_pair"),
    "generating_rsa_keys": ("ecp_lib.crypto", "generating_rsa_keys"),
    "issue_authentication_challenge": ("ecp_lib.auth.challenges", "issue_authentication_challenge"),
    "sign_payload": ("ecp_lib.crypto", "sign_payload"),
    "validate_rsa_keys": ("ecp_lib.crypto", "validate_rsa_keys"),
    "verify_authentication_response": ("ecp_lib.auth.challenges", "verify_authentication_response"),
    "verify_signature": ("ecp_lib.crypto", "verify_signature"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
