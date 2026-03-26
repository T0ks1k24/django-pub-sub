from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .challenges import verify_authentication_response
from ..core.exceptions import ECPError
from ..core.settings import get_ecp_auth_setting


class ECPAuthenticationBackend(BaseBackend):
    """Authenticate user by verifying ECP/RSA signature over one-time challenge."""

    def authenticate(
        self,
        request: Any,
        signature: str | None = None,
        challenge: str | None = None,
        identifier: str | None = None,
        user: Any = None,
        **kwargs: Any,
    ) -> Any | None:
        if not signature or not challenge:
            return None

        lookup_field = str(get_ecp_auth_setting("USER_LOOKUP_FIELD"))
        resolved_identifier = identifier or kwargs.get(lookup_field) or kwargs.get("username")
        resolved_user = user or self._get_user_by_identifier(resolved_identifier, lookup_field)

        if resolved_user is None or not self.user_can_authenticate(resolved_user):
            return None

        resolved_identifier = resolved_identifier or getattr(resolved_user, lookup_field, None)
        if not isinstance(resolved_identifier, str) or not resolved_identifier.strip():
            return None

        public_key_path = str(get_ecp_auth_setting("PUBLIC_KEY_FIELD"))
        public_key_pem = _resolve_attr(resolved_user, public_key_path)
        if not isinstance(public_key_pem, str) or not public_key_pem.strip():
            return None

        try:
            verify_authentication_response(
                identifier=resolved_identifier,
                challenge=challenge,
                signature=signature,
                public_key_pem=public_key_pem,
            )
        except ECPError:
            return None

        return resolved_user

    def get_user(self, user_id: Any) -> Any | None:
        user_model = get_user_model()
        try:
            return user_model._default_manager.get(pk=user_id)
        except user_model.DoesNotExist:
            return None

    def user_can_authenticate(self, user: Any) -> bool:
        return getattr(user, "is_active", True)

    def _get_user_by_identifier(self, identifier: str | None, lookup_field: str) -> Any | None:
        if not isinstance(identifier, str) or not identifier.strip():
            return None

        user_model = get_user_model()
        return user_model._default_manager.filter(**{lookup_field: identifier}).first()


def _resolve_attr(instance: Any, attr_path: str) -> Any:
    current = instance
    for attr in attr_path.split("."):
        current = getattr(current, attr, None)
        if current is None:
            return None
    return current
