from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth import authenticate

from .crypto import generate_keys, sign, verify
from .models import ECPKey
from .validators import sanitize, validate_public_key, validate_username


def create_user_keys(user: Any) -> str:
    """
    Генерує нову пару ключів для користувача.
    У БД зберігається тільки public key.
    Private key повертається як PEM-рядок, щоб view міг віддати його на скачування.
    """
    # Генеруємо нову пару ключів для щойно створеного користувача.
    # У БД кладемо тільки public key, а private key повертаємо назовні.
    private_key, public_key = generate_keys()
    validate_public_key(public_key)

    ECPKey.objects.update_or_create(
        user=user,
        defaults={"public_key": public_key},
    )
    return private_key


def create_challenge() -> str:
    """
    Повертає простий challenge для перевірки ключа.
    Використовується як payload для підпису приватним ключем.
    """
    # Простий одноразовий challenge, який використовується як payload для підпису.
    return f"login-test:{secrets.token_urlsafe(16)}"


def read_private_key(file: Any) -> str:
    """
    Читає private key з uploaded файлу Django.
    Повертає PEM як рядок.
    """
    # Працюємо з uploaded file без прив'язки до конкретного view.
    # Повертаємо просто PEM-рядок.
    if file is None:
        raise ValueError("Private key file is required.")

    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    if not isinstance(content, str):
        raise ValueError("Invalid private key file.")

    return sanitize(content)


def authenticate_with_private_key(
    request: Any,
    username: str,
    password: str,
    private_key: str,
) -> tuple[Any | None, str | None]:
    """
    1. Перевіряє username/password через стандартний Django authenticate
    2. Бере public key користувача з ECPKey
    3. Створює challenge
    4. Підписує challenge приватним ключем
    5. Перевіряє підпис через збережений public key
    """
    # Тут логіка навмисно не залежить від view:
    # на вході лише request, облікові дані і private key.
    try:
        username = validate_username(username)
        password = sanitize(password)
        private_key = sanitize(private_key)
    except ValueError as exc:
        return None, str(exc)

    # Спочатку перевіряємо стандартні username/password через Django.
    user = authenticate(request=request, username=username, password=password)
    if user is None:
        return None, "Invalid username or password."

    # Public key має вже бути прив'язаний до користувача в ECPKey.
    public_key = getattr(getattr(user, "ecp_key", None), "public_key", None)
    if not isinstance(public_key, str):
        return None, "Public key not found for user."

    try:
        validate_public_key(public_key)
    except ValueError as exc:
        return None, str(exc)

    # Створюємо test challenge і підписуємо його приватним ключем.
    challenge = create_challenge()
    try:
        signature = sign(private_key, challenge)
    except ValueError as exc:
        return None, str(exc)

    # Якщо public key з БД не підтверджує підпис, значить private key чужий або неправильний.
    if not verify(public_key, challenge, signature):
        return None, "Private key does not match stored public key."

    return user, None
