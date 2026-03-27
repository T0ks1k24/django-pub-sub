"""Middleware that validates ECP-related login payloads."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.http import JsonResponse

from .validators import sanitize, validate_username

logger = logging.getLogger(__name__)

_LOGIN_FIELDS = {"username", "password", "private_key", "private_key_file", "key_file"}


class ECPMiddleware:  # pylint: disable=too-few-public-methods
    """Reject malformed ECP login requests before they reach the view layer."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if request.method != "POST":
            return self.get_response(request)

        payload = self._get_payload(request)

        if (
            not _LOGIN_FIELDS & set(payload)
            and not _LOGIN_FIELDS & set(getattr(request, "FILES", {}))
        ):
            return self.get_response(request)

        errors = self._validate(request, payload)
        if errors:
            logger.warning(
                "ECPMiddleware validation failed: path=%s errors=%s",
                request.path,
                errors,
            )
            return JsonResponse({"detail": "Invalid request.", "errors": errors}, status=400)

        logger.debug("ECPMiddleware validation passed: path=%s", request.path)
        return self.get_response(request)

    def _validate(self, request: Any, payload: dict[str, Any]) -> list[str]:
        errors = []

        username = payload.get("username", "")
        try:
            validate_username(username)
        except ValueError as exc:
            errors.append(f"username: {exc}")

        password = payload.get("password", "")
        try:
            sanitize(password, max_length=256)
        except ValueError as exc:
            errors.append(f"password: {exc}")

        key_value = self._get_key(request, payload)
        if key_value is not None:
            try:
                sanitize(key_value, max_length=4096)
            except ValueError as exc:
                errors.append(f"private_key: {exc}")

        return errors

    def _get_key(self, request: Any, payload: dict[str, Any]) -> str | None:
        if value := payload.get("private_key"):
            return value

        files = getattr(request, "FILES", {})
        for field in ("private_key", "private_key_file", "key_file"):
            if uploaded_file := files.get(field):
                content = uploaded_file.read()
                uploaded_file.seek(0)
                return content.decode("utf-8") if isinstance(content, bytes) else content

        return None

    def _get_payload(self, request: Any) -> dict[str, Any]:
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8") or "{}")
                return data if isinstance(data, dict) else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}

        return request.POST.dict() if hasattr(request.POST, "dict") else dict(request.POST)
