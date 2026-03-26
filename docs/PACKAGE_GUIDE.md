# ecp-lib Package Guide

## Призначення бібліотеки

`ecp-lib` — це проста бібліотека для Django, яка допомагає винести криптографічну логіку з view у reusable код.

Бібліотека покриває три зони:

1. криптографія
2. валідація
3. інтеграція з Django через модель і middleware

## Що бібліотека робить

- генерує RSA ключі
- підписує payload приватним ключем
- перевіряє підпис через public key
- зберігає public key користувача
- читає private key з uploaded файлу
- допомагає аутентифікувати користувача через приватний ключ
- може рано блокувати невалідний login POST через middleware

## Що бібліотека не робить

- не створює URL
- не створює власні views
- не змушує змінювати існуючі `RegisterView` і `LoginView`
- не зберігає `private_key`

## Поточна структура

```text
ecp_lib/
  __init__.py
  auth.py
  crypto.py
  validators.py
  middleware.py
  models.py
  migrations/
```

## Модулі

### crypto.py

Низькорівневі криптографічні функції:

- `generate_keys()`
- `sign()`
- `verify()`

### validators.py

Функції перевірки і санітизації:

- `sanitize()`
- `validate_public_key()`
- `validate_username()`
- `validate_signature()`

### models.py

Модель:

- `ECPKey`

### middleware.py

Middleware:

- `ECPMiddleware`

### auth.py

Допоміжні функції для інтеграції з реєстрацією і логіном:

- `create_user_keys()`
- `read_private_key()`
- `create_challenge()`
- `verify_challenge()`
- `authenticate_with_private_key()`

## Модель ECPKey

```python
class ECPKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

Логіка проста:

- один користувач
- один `public_key`
- `private_key` не зберігається

## Встановлення

```bash
pip install ecp-lib
```

Для Django:

```bash
pip install "ecp-lib[django]"
```

## Django інтеграція

У `settings.py`:

```python
INSTALLED_APPS = [
    "ecp_lib",
]

MIDDLEWARE = [
    "ecp_lib.middleware.ECPMiddleware",
]
```

## Публічний API

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
    verify_challenge,
)
```

## Генерація ключів

```python
from ecp_lib.crypto import generate_keys

private_key, public_key = generate_keys()
```

Функція:

- генерує RSA 2048+
- повертає PEM рядки

Використовуються:

- RSA
- RSA-PSS
- SHA-256

## Підпис

```python
from ecp_lib.crypto import sign

signature = sign(private_key, "login-test")
```

Повертається:

- base64 рядок підпису

## Перевірка підпису

```python
from ecp_lib.crypto import verify

is_valid = verify(public_key, "login-test", signature)
```

## Валідація public key

```python
from ecp_lib.validators import validate_public_key

validate_public_key(public_key)
```

Що перевіряється:

- ключ є рядком
- PEM не пошкоджений
- ключ RSA
- довжина не менше 2048 біт

## sanitize

```python
from ecp_lib.validators import sanitize

value = sanitize(" alice ")
```

`sanitize()`:

- прибирає зайві пробіли
- блокує порожні значення
- блокує control characters
- блокує занадто довгі значення

## Реєстрація користувача

### create_user_keys

```python
from ecp_lib.auth import create_user_keys

private_key = create_user_keys(user)
```

Функція:

1. генерує `private_key/public_key`
2. зберігає `public_key` в `ECPKey`
3. повертає `private_key`

### Приклад у RegisterView

```python
from ecp_lib.auth import create_user_keys


class RegisterView(CreateView):
    ...

    def form_valid(self, form):
        response = super().form_valid(form)

        private_key = create_user_keys(self.object)

        response["Content-Disposition"] = 'attachment; filename="private.pem"'
        response.write(private_key)
        return response
```

## Читання private key із uploaded файлу

```python
from ecp_lib.auth import read_private_key

private_key = read_private_key(request.FILES["private_key"])
```

## Challenge helper-и

### create_challenge

```python
from ecp_lib.auth import create_challenge

challenge = create_challenge()
```

Повертає простий рядок для підпису.

### verify_challenge

```python
from ecp_lib.auth import verify_challenge

is_valid = verify_challenge(private_key, public_key, challenge)
```

Функція:

1. підписує challenge приватним ключем
2. перевіряє цей підпис через public key

Це зручно, якщо треба перевірити, що ключова пара коректна.

## authenticate_with_private_key

```python
from ecp_lib.auth import authenticate_with_private_key

user, error = authenticate_with_private_key(
    request=request,
    username="alice",
    password="secret",
    private_key=private_key_pem,
)
```

Функція робить:

1. перевіряє `username/password` через Django `authenticate`
2. знаходить `ECPKey` користувача
3. створює test challenge
4. підписує challenge приватним ключем
5. перевіряє підпис через збережений public key

Результат:

- `(user, None)` якщо все добре
- `(None, error_message)` якщо ні

## Middleware

`ECPMiddleware` перевіряє login POST запити.

Логіка:

1. якщо запит не `POST`, нічого не робить
2. якщо в запиті немає `signature`, нічого не робить
3. якщо `signature` є:
   - читає `username`
   - читає `signature`
   - бере `challenge` або `password` як payload
   - знаходить public key користувача
   - перевіряє RSA-підпис

Якщо перевірка не проходить:

- повертає `403`

Якщо проходить:

- пропускає запит далі

## Які поля очікує middleware

Для login POST:

- `username`
- `signature`
- `challenge` або `password`

## Безпека

Бібліотека використовує:

- RSA 2048+
- RSA-PSS
- SHA-256
- base64 для підпису
- PEM валідацію
- базову санітизацію input

Ключове правило:

- `private_key` не зберігається на сервері

## Приклад мінімальної інтеграції

### settings.py

```python
INSTALLED_APPS = [
    "ecp_lib",
]

MIDDLEWARE = [
    "ecp_lib.middleware.ECPMiddleware",
]
```

### RegisterView

```python
from ecp_lib.auth import create_user_keys


class RegisterView(CreateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        private_key = create_user_keys(self.object)
        response["Content-Disposition"] = 'attachment; filename="private.pem"'
        response.write(private_key)
        return response
```

### LoginView

```python
from ecp_lib.auth import authenticate_with_private_key, read_private_key


class LoginView(FormView):
    def form_valid(self, form):
        private_key = read_private_key(self.request.FILES["private_key"])

        user, error = authenticate_with_private_key(
            request=self.request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
            private_key=private_key,
        )

        if user is None:
            form.add_error(None, error)
            return self.form_invalid(form)

        return super().form_valid(form)
```

## Тести

```bash
python3 -m unittest discover -s tests -v
```
