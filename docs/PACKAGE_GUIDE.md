# ecp-lib Package Guide

## Призначення

`ecp-lib` — бібліотека для Django-проєктів, де користувач:

1. реєструється
2. отримує `private.pem`
3. під час логіну надсилає `username`, `password` і свій приватний ключ
4. сервер звіряє цей приватний ключ із `public_key`, який зберігається в БД

Бібліотека дає готові криптографічні helper-и, модель для `public_key` і middleware для ранньої перевірки запиту.

## Коротко про архітектуру

На сервері зберігається тільки `public_key`.
Приватний ключ сервер не генерує повторно і не повинен зберігати після відповіді користувачу.

Базовий flow такий:

- під час реєстрації сервер викликає `create_user_keys(user)`
- `public_key` записується в `ECPKey`
- `private_key` повертається як PEM і віддається користувачу
- під час логіну користувач надсилає `private.pem`
- middleware і/або view перевіряють, що цей ключ відповідає `public_key` користувача

## Структура пакета

```text
ecp_lib/
  __init__.py
  auth.py
  crypto.py
  middleware.py
  models.py
  validators.py
  migrations/
tests/
  test_ecp_lib.py
README.md
docs/PACKAGE_GUIDE.md
```

## Публічні компоненти

### `ecp_lib.crypto`

Низькорівневі криптографічні операції:

- `generate_keys()`
- `sign()`
- `verify()`

Алгоритм:

- RSA
- RSA-PSS
- SHA-256

### `ecp_lib.auth`

Високорівневі helper-и:

- `create_user_keys()`
- `read_private_key()`
- `authenticate_with_private_key()`
- `create_challenge()`
- `verify_challenge()`

Основний Django-flow використовує перші три.

### `ecp_lib.models`

Містить модель:

- `ECPKey`

### `ecp_lib.middleware`

Містить middleware:

- `ECPMiddleware`

### `ecp_lib.validators`

Містить валідацію вхідних даних:

- `sanitize()`
- `validate_username()`
- `validate_public_key()`
- `validate_signature()`

`validate_signature()` лишається як низькорівневий helper для криптографічних випадків, але не є центром поточного HTML login-flow.

## Модель `ECPKey`

[`ecp_lib/models.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/models.py)

```python
class ECPKey(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ecp_key",
    )
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

Властивості:

- один користувач має один `public_key`
- на сервері лежить тільки `public_key`
- `private.pem` має лишатися у користувача

## Криптографічний шар

### `generate_keys()`

```python
from ecp_lib.crypto import generate_keys

private_key, public_key = generate_keys()
```

Поведінка:

- генерує RSA-пару
- повертає PEM-рядки
- не дозволяє ключі коротші за `2048` біт

### `sign()`

```python
from ecp_lib.crypto import sign

signature = sign(private_key, "hello")
```

Результат: base64-рядок.

### `verify()`

```python
from ecp_lib.crypto import verify

is_valid = verify(public_key, "hello", signature)
```

Результат: `True` або `False`.

## Helper-и для Django flow

### `create_user_keys(user)`

```python
from ecp_lib.auth import create_user_keys

private_key = create_user_keys(user)
```

Функція:

1. генерує нову пару ключів
2. зберігає `public_key` в `ECPKey`
3. повертає `private_key`

Звичайний сценарій: віддати його користувачу як `private.pem`.

### `read_private_key(file)`

```python
from ecp_lib.auth import read_private_key

private_key = read_private_key(request.FILES["private_key_file"])
```

Функція:

- читає uploaded файл
- декодує його в UTF-8
- повертає PEM як рядок

### `authenticate_with_private_key(...)`

```python
from ecp_lib.auth import authenticate_with_private_key

user, error = authenticate_with_private_key(
    request=request,
    username=request.POST["username"],
    password=request.POST["password"],
    private_key=private_key,
)
```

Що робить:

1. валідовує вхідні дані
2. викликає Django `authenticate()`
3. бере `public_key` користувача
4. створює службовий payload
5. підписує його переданим `private_key`
6. перевіряє результат через `public_key`

Повертає:

- `(user, None)` якщо все добре
- `(None, error_message)` якщо щось не так

## Middleware

[`ecp_lib/middleware.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/middleware.py)

`ECPMiddleware` працює як ранній guard для `POST`-запитів.

Він запускає перевірку, якщо бачить:

- `username`
- `password`
- `private_key` як текст
- або uploaded файл `private_key`
- або uploaded файл `private_key_file`

Підтримувані content types:

- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`

Алгоритм:

1. переконатися, що це `POST`
2. дістати payload запиту
3. знайти `username`, `password` і приватний ключ
4. знайти `public_key` користувача
5. перевірити валідність `public_key`
6. згенерувати підпис із приватного ключа
7. перевірити його через `public_key`
8. повернути `403`, якщо перевірка не пройшла
9. пропустити запит у view, якщо перевірка пройшла

Практичне значення:

- middleware не логінить користувача
- middleware не замінює `login()`
- middleware відсікає биті або чужі ключі до того, як код дійде до бізнес-логіки view

## Логування middleware

Middleware пише лог у logger `ecp_lib.middleware`.

Щоб бачити його в Django, додай у `settings.py`:

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

У логах видно:

- що запит зайшов у middleware
- чому middleware був пропущений
- які ключі були в `POST` та `FILES`, якщо перевірка навіть не стартувала
- чому запит було відхилено
- коли перевірка пройшла успішно

## Мінімальна інтеграція в Django

У `settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "ecp_lib",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "ecp_lib.middleware.ECPMiddleware",
]
```

Потім:

```bash
python manage.py migrate
```

## Приклад логіну

```python
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect

from ecp_lib.auth import authenticate_with_private_key


class LoginView(DjangoLoginView):
    def form_valid(self, form):
        private_key = form.cleaned_data["private_key_file"].read().decode("utf-8")
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user, error = authenticate_with_private_key(
            self.request,
            username,
            password,
            private_key,
        )
        if error:
            form.add_error(None, error)
            return self.form_invalid(form)

        login(self.request, user)
        return redirect(self.get_success_url())
```

## Обмеження поточної реалізації

- немає challenge-response протоколу
- немає replay-protection поверх окремого одноразового challenge
- middleware спрацьовує на будь-який `POST`, якщо бачить відповідні ECP-поля
- якщо view окремо викликає `authenticate_with_private_key()`, перевірка відбувається двічі: у middleware і у view

Останній пункт не є багом сам по собі, але його треба враховувати в архітектурі.

## Тестування

[`tests/test_ecp_lib.py`](/home/toksik/Developer/hackaton/django-pub-sub/tests/test_ecp_lib.py) покриває:

- генерацію ключів
- підпис і перевірку
- створення ключів користувача
- читання `private.pem`
- перевірку `authenticate_with_private_key()`
- middleware для `private_key`
- middleware для uploaded `private_key`
- middleware для uploaded `private_key_file`

Запуск:

```bash
pytest -q
```

## Безпека

- не зберігай `private.pem` на сервері
- віддавай `private.pem` тільки власнику після реєстрації
- використовуйте HTTPS
- перевіряй валідність `public_key` перед збереженням
- не вважай middleware заміною повної аутентифікації у view
