from __future__ import annotations

import json
import logging
from typing import Any

from django.http import JsonResponse

from .crypto import sign, verify
from .models import ECPKey
from .validators import sanitize, validate_public_key, validate_username

logger = logging.getLogger(__name__)


class ECPMiddleware:
    """
    Перевіряє private key для POST-запитів, які несуть ECP-поля.
    Підтримує form-data/x-www-form-urlencoded та application/json.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        logger.debug(
            "ECP middleware entered: method=%s path=%s content_type=%s",
            getattr(request, "method", None),
            getattr(request, "path", None),
            getattr(request, "content_type", None),
        )

        if request.method != "POST":
            logger.debug("ECP middleware skipped non-POST request: path=%s", getattr(request, "path", None))
            return self.get_response(request)

        payload_data = self._get_payload_data(request)
        username = payload_data.get("username")
        auth_proof = self._get_auth_proof(request, payload_data)
        if not username or auth_proof is None:
            logger.debug(
                "ECP middleware skipped request without required fields: path=%s has_username=%s has_auth_proof=%s post_keys=%s file_keys=%s",
                getattr(request, "path", None),
                bool(username),
                auth_proof is not None,
                sorted(getattr(payload_data, "keys", lambda: [])()),
                sorted(getattr(getattr(request, "FILES", None), "keys", lambda: [])()),
            )
            return self.get_response(request)

        payload = payload_data.get("password")
        if not payload:
            logger.warning(
                "ECP middleware rejected request without password payload: path=%s username=%s",
                getattr(request, "path", None),
                username,
            )
            return JsonResponse({"detail": "Missing password payload."}, status=403)

        try:
            username = validate_username(username)
            payload = sanitize(payload)
        except ValueError as exc:
            logger.warning(
                "ECP middleware rejected invalid authentication payload: path=%s username=%s error=%s",
                getattr(request, "path", None),
                username,
                exc,
            )
            return JsonResponse({"detail": "Invalid authentication payload."}, status=403)

        stored_key = (
            ECPKey.objects.filter(user__username=username)
            .values_list("public_key", flat=True)
            .first()
        )
        if not isinstance(stored_key, str):
            logger.warning(
                "ECP middleware could not find public key: path=%s username=%s",
                getattr(request, "path", None),
                username,
            )
            return JsonResponse({"detail": "Public key not found."}, status=403)

        try:
            validate_public_key(stored_key)
        except ValueError as exc:
            logger.warning(
                "ECP middleware found invalid stored public key: path=%s username=%s error=%s",
                getattr(request, "path", None),
                username,
                exc,
            )
            return JsonResponse({"detail": "Invalid public key."}, status=403)

        try:
            signature = self._resolve_signature(auth_proof, payload)
        except ValueError as exc:
            logger.warning(
                "ECP middleware failed to resolve signature from private key: path=%s username=%s error=%s",
                getattr(request, "path", None),
                username,
                exc,
            )
            return JsonResponse({"detail": "Invalid authentication payload."}, status=403)

        if not verify(stored_key, payload, signature):
            logger.warning(
                "ECP middleware signature verification failed: path=%s username=%s proof_type=%s",
                getattr(request, "path", None),
                username,
                auth_proof[0],
            )
            return JsonResponse({"detail": "Invalid signature."}, status=403)

        logger.info(
            "ECP middleware verification passed: path=%s username=%s proof_type=%s",
            getattr(request, "path", None),
            username,
            auth_proof[0],
        )
        return self.get_response(request)

    def _get_auth_proof(self, request: Any, payload_data: dict[str, Any]) -> tuple[str, Any] | None:
        private_key = payload_data.get("private_key")
        if private_key:
            return ("private_key", private_key)

        uploaded_key = None
        if hasattr(request, "FILES"):
            uploaded_key = request.FILES.get("private_key") or request.FILES.get("private_key_file")
        if uploaded_key is not None:
            return ("private_key_file", uploaded_key)

        return None

    def _resolve_signature(self, auth_proof: tuple[str, Any], payload: str) -> str:
        proof_type, proof_value = auth_proof

        if proof_type == "private_key_file":
            content = proof_value.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            if not isinstance(content, str):
                raise ValueError("Invalid private key file.")
            proof_value = content

        private_key = sanitize(proof_value)
        return sign(private_key, payload)

    def _get_payload_data(self, request: Any) -> dict[str, Any]:
        if request.content_type == "application/json":
            try:
                body = request.body.decode("utf-8")
                data = json.loads(body) if body else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning(
                    "ECP middleware received invalid JSON body: path=%s",
                    getattr(request, "path", None),
                )
                return {}
            return data if isinstance(data, dict) else {}

        return request.POST
