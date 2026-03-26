from __future__ import annotations

from importlib import import_module

# Кореневий модуль нічого не імпортує напряму, а працює через lazy imports.
# Це важливо для Django, щоб пакет безпечно підключався через INSTALLED_APPS
# і не тягнув моделі занадто рано під час apps.populate().
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
    "verify_challenge",
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
    "verify_challenge": ("ecp_lib.auth", "verify_challenge"),
    "verify": ("ecp_lib.crypto", "verify"),
}


def __getattr__(name: str):
    # Ледачий імпорт дозволяє працювати з API як з "плоским" пакетом,
    # але не створює проблем під час старту Django.
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
