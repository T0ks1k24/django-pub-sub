# ecp-lib

`ecp-lib` — Python бібліотека для RSA/ЕЦП, підписів, challenge-response та опційної інтеграції з Django auth backend.

Пакет експортує стабільний Python namespace `ecp_lib` і встановлює консольну команду `ecp-lib`.

## Встановлення

Базова бібліотека:

```bash
pip install ecp-lib
```

З Django-інтеграцією:

```bash
pip install "ecp-lib[django]"
```

Для локальної розробки:

```bash
pip install -e .
```

## Структура пакету

```text
ecp_lib/
  __init__.py
  auth/
    backend.py
    challenges.py
  crypto/
    keys.py
    signatures.py
  core/
    exceptions.py
    settings.py
    validators.py
  cli.py
```

Сумісність:
- `ecp_lib` є канонічним namespace для імпортів.
- Crypto API та CLI працюють без встановленого `django`.
- Django backend, challenges і `AppConfig` доступні при встановленому extra `django`.

## Django інтеграція

```python
INSTALLED_APPS = [
    # ...
    "ecp_lib",
]

MIDDLEWARE = [
    # ...
    "ecp_lib.middleware.AttachUserPublicKeyMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "ecp_lib.backends.ECPAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ECP_AUTH = {
    "USER_LOOKUP_FIELD": "username",
    "PUBLIC_KEY_FIELD": "ecp_public_key.public_key",
    "CHALLENGE_TTL_SECONDS": 300,
    "CHALLENGE_CLOCK_SKEW_SECONDS": 30,
    "IDENTIFIER_MAX_LENGTH": 150,
    "MAX_SIGNATURE_LENGTH": 8192,
}
```

Модель ключа:

```python
from ecp_lib.models import ECPUserPublicKey

ECPUserPublicKey.objects.update_or_create(
    user=user,
    defaults={"public_key": public_key_pem},
)
```

Приклад авторизації:

```python
from django.contrib.auth import authenticate
from ecp_lib import issue_authentication_challenge

challenge = issue_authentication_challenge("alice")
# Клієнт підписує challenge.challenge приватним ключем

user = authenticate(
    request=request,
    identifier="alice",
    challenge=challenge.challenge,
    signature=signature_from_client,
)
```

## CLI (Entry Point)

Після встановлення пакет реєструє entry point:

```bash
ecp-lib --help
```

Альтернатива без встановленого script wrapper:

```bash
python -m ecp_lib.cli --help
```

### Генерація ключів

```bash
ecp-lib generate-keys --format pem
```

```bash
ecp-lib generate-keys --format json
```

### Валідація пари ключів

```bash
ecp-lib validate-keys --private-key-file private.pem --public-key-file public.pem
```

### Підпис payload

```bash
ecp-lib sign --private-key-file private.pem --payload "hello"
```

```bash
ecp-lib sign --private-key-file private.pem --payload-file payload.txt
```

### Перевірка підпису

```bash
ecp-lib verify --public-key-file public.pem --payload "hello" --signature "<base64>"
```

```bash
ecp-lib verify --public-key-file public.pem --payload-file payload.txt --signature "<base64>"
```

Коди завершення CLI:
- `0` — успіх
- `1` — підпис невалідний (`verify`)
- `2` — помилка вводу/валідації/виконання

## Безпека

- One-time challenge + anti-replay через cache.
- Валідація формату identifier, payload і signature.
- RSA-PSS + SHA-256 для підпису/верифікації.
- Деталізовані structured exceptions для розробників.

## Тести

```bash
python3 -m unittest discover -s tests -v
```

Розширена документація: `docs/PACKAGE_GUIDE.md`.
