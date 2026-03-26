from __future__ import annotations

from typing import Any, Callable

from ..core.settings import get_ecp_auth_setting


class AttachUserPublicKeyMiddleware:
    """
    Attach resolved public key data to request and authenticated user objects.

    Sets:
    - request.ecp_public_key_obj
    - request.ecp_public_key
    """

    def __init__(self, get_response: Callable[[Any], Any]):
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        self._attach_user_public_key(request)
        return self.get_response(request)

    def _attach_user_public_key(self, request: Any) -> None:
        setattr(request, "ecp_public_key_obj", None)
        setattr(request, "ecp_public_key", None)

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return

        public_key_path = str(get_ecp_auth_setting("PUBLIC_KEY_FIELD"))
        public_key = _resolve_attr(user, public_key_path)
        if not isinstance(public_key, str) or not public_key.strip():
            return

        setattr(request, "ecp_public_key", public_key)
        if "." in public_key_path:
            relation_attr = public_key_path.split(".", 1)[0]
            setattr(request, "ecp_public_key_obj", getattr(user, relation_attr, None))

        if getattr(user, "public_key", None) is None:
            setattr(user, "public_key", public_key)


def _resolve_attr(instance: Any, attr_path: str) -> Any:
    current = instance
    for attr in attr_path.split("."):
        current = getattr(current, attr, None)
        if current is None:
            return None
    return current
