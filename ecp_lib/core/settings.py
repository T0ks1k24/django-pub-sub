from __future__ import annotations

from typing import Any, Final

try:
    from django.conf import settings as django_settings
except ImportError:  # pragma: no cover - exercised in non-Django environments
    django_settings = None


DEFAULT_ECP_AUTH_SETTINGS: Final[dict[str, Any]] = {
    "CACHE_PREFIX": "ecp-auth",
    "CHALLENGE_TTL_SECONDS": 300,
    "CHALLENGE_CLOCK_SKEW_SECONDS": 30,
    "PUBLIC_KEY_FIELD": "public_key",
    "USER_LOOKUP_FIELD": "username",
    "IDENTIFIER_MAX_LENGTH": 150,
    "ALLOWED_IDENTIFIER_CHARS": r"^[A-Za-z0-9_.@-]+$",
    "MAX_SIGNATURE_LENGTH": 8192,
}


def get_ecp_auth_setting(name: str) -> Any:
    """Read an ECP setting from Django settings with project defaults."""
    if name not in DEFAULT_ECP_AUTH_SETTINGS:
        raise KeyError(f"Unknown ECP setting: {name}")

    if django_settings is None or not django_settings.configured:
        return DEFAULT_ECP_AUTH_SETTINGS[name]

    config = getattr(django_settings, "ECP_AUTH", {})
    return config.get(name, DEFAULT_ECP_AUTH_SETTINGS[name])
