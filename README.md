# ecp-lib

`ecp-lib` — Django-бібліотека для входу з `username + password + private.pem`.
Вона генерує RSA-ключі, зберігає `public_key` користувача і дає middleware, яке перевіряє, що завантажений приватний ключ відповідає ключу в БД.

## Що вміє бібліотека

- генерувати пару `private_key/public_key`
- зберігати `public_key` у моделі `ECPKey`
- читати `private.pem` з upload
- перевіряти пару `username/password/private_key`
- відсікати невалідні логін-запити ще в middleware
- логувати, чи запит взагалі дійшов до middleware і на якому кроці впав

## Що бібліотека не робить

- не дає готових `views` або `urls`
- не логінить користувача сама по собі
- не зберігає `private.pem` на сервері
- не будує challenge-response протокол

## Встановлення

```bash
pip install ecp-lib
pip install "ecp-lib[django]"
```

## Публічне API

```python
from ecp_lib import (
    ECPKey,
    ECPMiddleware,
    authenticate_with_private_key,
    create_challenge,
    create_user_keys,
    generate_keys,
    read_private_key,
    sanitize,
    sign,
    validate_public_key,
    verify,
)
```

Основний Django-flow використовує:

- `create_user_keys()`
- `read_private_key()`
- `authenticate_with_private_key()`
- `ECPMiddleware`

## Основний flow

### 1. Реєстрація

Після створення користувача виклич `create_user_keys(user)`.
Функція:

1. генерує нову RSA-пару
2. зберігає `public_key` у `ECPKey`
3. повертає `private_key` як PEM-рядок

Типовий варіант: віддати цей PEM користувачу як файл `private.pem`.

```python
from django.http import HttpResponse

from ecp_lib.auth import create_user_keys


def register_success_response(user):
    private_key = create_user_keys(user)

    response = HttpResponse(private_key, content_type="application/x-pem-file")
    response["Content-Disposition"] = 'attachment; filename="private.pem"'
    return response
```

### 2. Логін

Форма логіну надсилає:

- `username`
- `password`
- файл `private_key` або `private_key_file`

У view можна зчитати PEM і перевірити його через helper:

```python
from django.contrib.auth import login
from django.shortcuts import redirect

from ecp_lib.auth import authenticate_with_private_key, read_private_key


def login_view(request):
    if request.method == "POST":
        private_key = read_private_key(
            request.FILES["private_key_file"]
        )

        user, error = authenticate_with_private_key(
            request=request,
            username=request.POST["username"],
            password=request.POST["password"],
            private_key=private_key,
        )

        if error:
            ...

        login(request, user)
        return redirect("dashboard")

    ...
```

`authenticate_with_private_key()`:

1. валідовує вхідні дані
2. перевіряє `username/password` через Django `authenticate()`
3. бере `public_key` користувача з `ECPKey`
4. створює службовий payload
5. підписує його переданим `private_key`
6. перевіряє підпис через збережений `public_key`

Повертає:

- `(user, None)` при успіху
- `(None, "error text")` при помилці

## Middleware

[`ecp_lib/middleware.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/middleware.py) працює як ранній guard для `POST`-запитів.

Middleware реагує на запит, якщо бачить:

- `username`
- `password`
- `private_key` як текстове поле або файл `private_key`
- або файл `private_key_file`

Підтримувані content types:

- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`

Що воно робить:

1. перевіряє, що це `POST`
2. зчитує `username`, `password` і приватний ключ
3. знаходить `public_key` користувача в БД
4. генерує підпис з переданого приватного ключа
5. перевіряє підпис через `public_key`
6. при помилці повертає `403`
7. при успіху пропускає запит далі у view

Важливо:

- middleware не створює сесію користувача
- middleware не замінює `django.contrib.auth.login`
- middleware лише відсікає невалідні запити до того, як вони дійдуть до view

## Підключення до Django

У `settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "ecp_lib",
]

MIDDLEWARE = [
    "...",
    "ecp_lib.middleware.ECPMiddleware",
]
```

Після цього виконай міграції:

```bash
python manage.py migrate
```

## Логування middleware

Щоб бачити, чи middleware спрацьовує, додай logger у `settings.py`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "ecp_lib.middleware": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
```

У логах буде видно:

- що запит зайшов у middleware
- чому middleware пропустив запит
- чому middleware відхилив запит
- чи перевірка пройшла успішно

## Криптографічні helper-и

### `generate_keys()`

```python
from ecp_lib.crypto import generate_keys

private_key, public_key = generate_keys()
```

- повертає PEM-рядки
- генерує тільки RSA-ключі
- мінімальна довжина ключа: `2048`

### `sign()` і `verify()`

```python
from ecp_lib.crypto import sign, verify

signature = sign(private_key, "hello")
is_valid = verify(public_key, "hello", signature)
```

Бібліотека використовує RSA-PSS + SHA-256.

### `create_challenge()` і `verify_challenge()`

Це допоміжні helper-и для тестів або локальної перевірки пари ключів.
Вони не є основою поточного login-flow через HTML-форму.

## Валідація

[`ecp_lib/validators.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/validators.py) містить:

- `sanitize(value)`
- `validate_username(username)`
- `validate_public_key(public_key)`

Перевіряється:

- тип і непорожність значення
- відсутність небезпечних control characters
- PEM-формат `public_key`
- RSA-тип ключа
- мінімальна довжина ключа `2048`

## Модель

[`ecp_lib/models.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/models.py):

```python
class ECPKey(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ecp_key")
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

На сервері зберігається тільки `public_key`.

## Тести

Запуск:

```bash
pytest -q
```

Покрито:

- генерацію ключів
- підпис і перевірку
- збереження `public_key`
- читання `private.pem`
- helper-и з `auth.py`
- middleware для form POST
- middleware для JSON POST

## Безпека

- не зберігай `private.pem` у БД
- віддавай `private.pem` користувачу тільки один раз після реєстрації
- перевіряй, що в БД лежить тільки валідний `public_key`
- використовуй HTTPS, бо `password` і файл ключа передаються на сервер
- middleware варто ставити як ранній бар'єр, але не замість перевірки у view
