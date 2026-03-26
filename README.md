# ecp-lib

`ecp-lib` — це невелика Django-бібліотека для роботи з RSA ЕЦП.

Вона дає:

- генерацію RSA ключів
- підпис payload приватним ключем
- перевірку підпису через public key
- модель для збереження public key користувача
- middleware для перевірки RSA-підпису при login POST
- helper-функції для інтеграції в реєстрацію і логін

Бібліотека не створює:

- свої views
- свої urls
- service layer
- складну архітектуру

## Структура

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

## Встановлення

```bash
pip install ecp-lib
```

Для Django:

```bash
pip install "ecp-lib[django]"
```

## Django налаштування

У `settings.py`:

```python
INSTALLED_APPS = [
    "ecp_lib",
]

MIDDLEWARE = [
    "ecp_lib.middleware.ECPMiddleware",
]
```

## Основний API

Через кореневий пакет:

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

Що використовується:

- RSA 2048+
- RSA-PSS
- SHA-256
- base64 для підпису

## Підпис і перевірка

```python
from ecp_lib.crypto import sign, verify

signature = sign(private_key, "hello")
is_valid = verify(public_key, "hello", signature)
```

## Валідація

### sanitize

```python
from ecp_lib.validators import sanitize

value = sanitize(" alice ")
```

### validate_public_key

```python
from ecp_lib.validators import validate_public_key

validate_public_key(public_key)
```

Функція перевіряє:

- PEM формат
- що ключ RSA
- що ключ не менше 2048 біт

## Модель

```python
from ecp_lib.models import ECPKey
```

```python
class ECPKey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

У БД зберігається тільки `public_key`.

`private_key` сервер не зберігає.

## Реєстрація користувача

Якщо логіку реєстрації хочеш тримати у своєму view, але генерацію ключів винести в бібліотеку:

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

Що робить `create_user_keys(user)`:

1. генерує нову пару ключів
2. зберігає `public_key` в `ECPKey`
3. повертає `private_key` як PEM-рядок

## Читання private key із файлу

```python
from ecp_lib.auth import read_private_key

private_key = read_private_key(request.FILES["private_key"])
```

## Аутентифікація з приватним ключем

```python
from ecp_lib.auth import authenticate_with_private_key

user, error = authenticate_with_private_key(
    request=request,
    username="alice",
    password="secret",
    private_key=private_key_pem,
)
```

Що робить ця функція:

1. перевіряє `username/password` через Django `authenticate`
2. знаходить `ECPKey` користувача
3. створює test challenge
4. підписує challenge приватним ключем
5. перевіряє підпис через збережений `public_key`

Повертає:

- `(user, None)` якщо все добре
- `(None, "error text")` якщо перевірка не пройшла

## Challenge helper-и

### create_challenge

```python
from ecp_lib.auth import create_challenge

challenge = create_challenge()
```

### verify_challenge

```python
from ecp_lib.auth import verify_challenge

is_valid = verify_challenge(private_key, public_key, challenge)
```

Це корисно, коли треба перевірити, що ключова пара справді відповідає одна одній.

## Middleware

`ECPMiddleware` не створює логін і не змінює стандартний `LoginView`.

Воно просто:

1. спрацьовує тільки на `POST`
2. якщо в запиті немає `signature`, нічого не чіпає
3. якщо є `signature`, бере:
   - `username`
   - `signature`
   - `challenge` або `password`
4. знаходить `public_key` користувача
5. перевіряє підпис
6. якщо щось не так, повертає `403`

## Які поля очікує middleware

Для login POST:

- `username`
- `signature`
- `challenge` або `password`

## Приклад LoginView

```python
class LoginView(DjangoLoginView):
    ...
```

Нічого міняти не потрібно, якщо вся RSA-перевірка вже йде через middleware або через виклик `authenticate_with_private_key(...)` у власній логіці.

## Безпека

Бібліотека використовує:

- RSA 2048+
- RSA-PSS
- SHA-256
- base64 підпис
- перевірку PEM
- санітизацію input

Не зберігається:

- `private_key`

Зберігається:

- тільки `public_key`

## Тести

```bash
python3 -m unittest discover -s tests -v
```

Детальніша документація: `docs/PACKAGE_GUIDE.md`.
