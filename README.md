# ecp-lib

`ecp-lib` is a Django library for authentication using `username + password + private.pem`.
It generates RSA keys, stores the user’s `public_key`, and provides middleware that verifies the uploaded private key matches the key in the database.

## What the library can do

- generate a `private_key/public_key` pair 
- store the `public_key` in the `ECPKey` model
- read `private.pem` from upload
- validate the `username/password/private_key` combination
- reject invalid login requests at the middleware level
- log whether the request reached the middleware at all and at which step it failed

## What the library does not do

- does not provide ready-made `views` or `urls`
- does not log in the user by itself
- does not store `private.pem` on the server
- does not implement a challenge-response protocol

## Installation

```bash
pip install ecp-lib
pip install "ecp-lib[django]"
```

## Public API

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

The main Django-flow uses:

## Main Django flow

## Main flow

### 1. Registration

After creating a user, call `create_user_keys(user)`.
The function:

1. generates a new RSA key pair
2. stores the `public_key` in `ECPKey`
3. returns the `private_key` as a PEM string

Typical approach: provide this PEM to the user as a `private.pem` file.

```python
from django.http import HttpResponse

from ecp_lib.auth import create_user_keys


def registration_success(request, user):
    private_key = create_user_keys(user)

    response = HttpResponse(private_key, content_type="application/x-pem-file")
    response["Content-Disposition"] = 'attachment; filename="private.pem"'
    return response
```

### 2. Login

The login form submits:

- `username`
- `password`
- a `private_key` or `private_key_file`

In the view, you can read the PEM and verify it using the helper:

```python
from django.contrib.auth import login
from django.shortcuts import redirect, render

from ecp_lib.auth import authenticate_with_private_key, read_private_key


def login_view(request):
    if request.method == "POST":
        private_key = read_private_key(request.FILES["private_key_file"])

        user, error = authenticate_with_private_key(
            request=request,
            username=request.POST["username"],
            password=request.POST["password"],
            private_key=private_key,
        )

        if error:
            return render(request, "login.html", {"error": error}, status=400)

        login(request, user)
        return redirect("dashboard")

    return render(request, "login.html")
```

`authenticate_with_private_key(...)`:

1. validates the input data
2. checks `username/password` using Django’s `authenticate()`
3. retrieves the user’s `public_key` from `ECPKey`
4. creates an internal payload
5. signs it with the provided `private_key`
6. verifies the signature using the stored `public_key`

Returns:

- `(user, None)` on success
- `(None, "error text")` on failure

## Middleware

[`ecp_lib/middleware.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/middleware.py) acts as an early guard for `POST` requests.

The middleware triggers when it detects:

- `username`
- `password`
- `private_key` as a text field or a `private_key` file
- or a `private_key_file`

Supported content types:

- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`

What it does:

1. checks that the request is a `POST`
2. reads `username`, `password`, and the private key
3. retrieves the user’s `public_key` from the database
4. generates a signature using the provided private key
5. verifies the signature with the `public_key`
6. returns `403` on failure
7. allows the request to proceed to the view on success

Important:

- the middleware does not create a user session
- the middleware does not replace `django.contrib.auth.login`
- the middleware only blocks invalid requests before they reach the view

## Django integration

In `settings.py`:

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

After that, run the migrations:

```bash
python manage.py migrate
```

## Middleware Logging

To see if the middleware is triggered, add a logger in `settings.py`:

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

The logs will show:

- that the request reached the middleware
- why the middleware allowed the request
- why the middleware rejected the request
- whether the verification succeeded

## Cryptographic Helpers

### `generate_keys()`

```python
from ecp_lib.crypto import generate_keys

private_key, public_key = generate_keys()
```

- returns PEM strings
- generates only RSA keys
- minimum key length: `2048`

### `sign()` & `verify()`

```python
from ecp_lib.crypto import sign, verify

signature = sign(private_key, "hello")
is_valid = verify(public_key, "hello", signature)
```

The library uses `RSA-PSS` with `SHA-256`.

### `create_challenge()` & `verify_challenge()`

These are auxiliary helpers for testing or local verification of key pairs.
They are not part of the main login flow via the HTML form.

## Validation

[`ecp_lib/validators.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/validators.py) contains:

- `sanitize(value)`
- `validate_username(username)`
- `validate_public_key(public_key)`

It validates:

- the type and non-emptiness of the value
- absence of dangerous control characters
- PEM format of the `public_key`
- RSA key type
- minimum key length of `2048`

## Model

`ECPKey` stores:

- `user` as `OneToOneField`;
- `public_key` as `TextField`;
- `created_at` as `DateTimeField(auto_now_add=True)`.

Only the `public_key` is stored on the server.

## Tests

Run:

```bash
pytest -q
```

Coverage:

- key generation
- signing and verification
- storing the `public_key`
- reading `private.pem`
- helpers from `auth.py`
- middleware for form POST
- middleware for JSON POST

## Security

- do not store `private.pem` in the database
- provide the `private.pem` to the user only once after registration
- ensure only a valid `public_key` is stored in the database
- use HTTPS, since the password and key file are sent to the server
- place the middleware as an early barrier, but not as a replacement for verification in the view

