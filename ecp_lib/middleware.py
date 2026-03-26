from __future__ import annotations

from typing import Any

from django.http import JsonResponse

from .crypto import verify
from .models import ECPKey
from .validators import sanitize, validate_public_key, validate_signature, validate_username


class ECPMiddleware:
    """
    Перевіряє RSA-підпис для login POST запитів.
    Якщо в запиті немає signature, middleware нічого не ламає і просто пропускає його далі.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        # Middleware втручається тільки в POST-запити.
        # Усі інші запити проходять без змін.
        if request.method != "POST":
            return self.get_response(request)

        # Якщо signature не переданий, значить це не ECP-логін,
        # тому запит не треба чіпати.
        username = request.POST.get("username")
        signature = request.POST.get("signature")
        if not username or not signature:
            return self.get_response(request)

        # Payload для перевірки — це або окремий challenge, або password поле.
        payload = request.POST.get("challenge") or request.POST.get("password")
        if not payload:
            return JsonResponse({"detail": "Missing challenge or password payload."}, status=403)

        # Спочатку перевіряємо всі вхідні значення.
        try:
            username = validate_username(username)
            signature = validate_signature(signature)
            payload = sanitize(payload)
        except ValueError:
            return JsonResponse({"detail": "Invalid authentication payload."}, status=403)

        # Дістаємо з БД public key конкретного користувача.
        stored_key = (
            ECPKey.objects.filter(user__username=username)
            .values_list("public_key", flat=True)
            .first()
        )
        if not isinstance(stored_key, str):
            return JsonResponse({"detail": "Public key not found."}, status=403)

        # Якщо ключ у БД зламаний або пошкоджений, логін одразу блокуємо.
        try:
            validate_public_key(stored_key)
        except ValueError:
            return JsonResponse({"detail": "Invalid public key."}, status=403)

        # Фінальна криптографічна перевірка підпису.
        if not verify(stored_key, payload, signature):
            return JsonResponse({"detail": "Invalid signature."}, status=403)

        return self.get_response(request)
