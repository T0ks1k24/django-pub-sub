# ecp-lib Package Guide

## Purpose

`ecp-lib` is a small package for Django projects that need:

- RSA key generation for each user;
- server-side storage of only the public key;
- a helper that checks whether a provided private key matches the stored public key after Django password authentication;
- middleware that validates ECP-related login request payloads before the view handles them.

The package is intentionally narrow. It ships primitives and integration helpers, not a complete auth product.

## Package structure

```text
ecp_lib/
  __init__.py
  apps.py
  auth.py
  crypto.py
  middleware.py
  models.py
  validators.py
  migrations/
    0001_initial.py
tests/
  test_auth.py
  test_crypto.py
  test_middleware.py
  test_validators.py
README.md
docs/PACKAGE_GUIDE.md
```

## Components

### `ecp_lib.crypto`

Low-level cryptographic helpers:

- `generate_keys(key_size=2048)`
- `sign(private_key, payload)`
- `verify(public_key, payload, signature)`

Implementation:

- RSA keys only;
- minimum RSA key size is `2048`;
- signatures use RSA-PSS with SHA-256;
- `sign()` returns a base64 string;
- `verify()` returns `True` or `False`.

### `ecp_lib.validators`

Input validation helpers:

- `sanitize(value)`
- `validate_username(username)`
- `validate_public_key(key)`

Validation rules:

- values must be strings;
- values cannot be empty after trimming;
- values longer than `8192` are rejected;
- control characters are rejected, except `\n`, `\r`, and `\t`;
- usernames must match `^[A-Za-z0-9_.@-]{1,150}$`;
- public keys must be PEM-encoded RSA public keys and at least `2048` bits.

### `ecp_lib.models`

Contains the `ECPKey` model:

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

Design intent:

- one user has one stored public key;
- only the public key is persisted;
- the private key stays with the user.

### `ecp_lib.auth`

High-level helpers for the Django flow:

- `create_user_keys(user)`
- `create_challenge()`
- `read_private_key(file)`
- `authenticate_with_private_key(request, username, password, private_key)`

Behavior summary:

- `create_user_keys()` generates a fresh key pair, validates the public key, stores it through `ECPKey.objects.update_or_create(...)`, and returns the private key PEM;
- `create_challenge()` returns a new string in the format `login-test:<token>`;
- `read_private_key()` reads an uploaded Django file, decodes UTF-8 bytes, sanitizes the result, and returns the PEM string;
- `authenticate_with_private_key()` validates the inputs, calls Django `authenticate(...)`, reads the stored public key from `user.ecp_key`, signs a generated challenge, and verifies that signature with the stored public key.

Return contract of `authenticate_with_private_key()`:

- success: `(user, None)`
- failure: `(None, error_message)`

Typical failure reasons:

- invalid username or password;
- missing `ECPKey` for the user;
- malformed public key in storage;
- invalid private key PEM;
- provided private key does not match the stored public key.

### `ecp_lib.middleware`

Contains `ECPMiddleware`.

This middleware is an input validator, not an authenticator.

It activates only for `POST` requests that contain at least one of these fields in body data or uploaded files:

- `username`
- `password`
- `private_key`
- `private_key_file`
- `key_file`

Supported request bodies:

- form-urlencoded;
- multipart form-data;
- JSON.

Validation flow:

1. Ignore non-`POST` requests.
2. Parse the payload from `request.POST` or JSON body.
3. If no ECP-related fields are present, skip the request.
4. Validate `username`.
5. Sanitize `password`.
6. Read the private key from a text field or uploaded file if one exists.
7. Sanitize the private key value.
8. Return `JsonResponse({"detail": "Invalid request.", "errors": [...]}, status=400)` on failure.
9. Call the next middleware or view on success.

Important implementation details:

- the middleware does not query `ECPKey`;
- it does not verify signatures;
- it does not call Django auth APIs;
- uploaded files are rewound with `seek(0)` after reading.

## Root package API

`ecp_lib.__init__` exposes a flat API via lazy imports:

- `ECPKey`
- `ECPMiddleware`
- `authenticate_with_private_key`
- `create_challenge`
- `create_user_keys`
- `generate_keys`
- `read_private_key`
- `sanitize`
- `sign`
- `validate_public_key`
- `verify`

This keeps the import ergonomics simple while avoiding early model imports during Django app loading.

## Minimal Django integration

Add the app and middleware:

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

Run migrations:

```bash
python manage.py migrate
```

Registration example:

```python
from django.http import HttpResponse

from ecp_lib.auth import create_user_keys


def registration_success(request, user):
    private_key = create_user_keys(user)
    response = HttpResponse(private_key, content_type="application/x-pem-file")
    response["Content-Disposition"] = 'attachment; filename="private.pem"'
    return response
```

Login example:

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

## Logging

`ECPMiddleware` uses the `ecp_lib.middleware` logger.

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

## Tests

The current test suite covers:

- key generation and minimum key size;
- signing and signature verification;
- sanitization and username validation;
- public key validation;
- `create_user_keys()` behavior;
- uploaded private key reading;
- challenge generation;
- `authenticate_with_private_key()` success and failure cases;
- middleware pass-through and validation failure behavior.

Run:

```bash
pytest -q
```

## Boundaries and limitations

- no built-in forms, views, or templates;
- no storage for challenges or replay prevention state;
- no automatic user login;
- middleware validates request shape only and should not be treated as proof that the key matches the stored public key.

## Security notes

- do not persist `private.pem` on the server;
- return the private key only when it is first generated;
- require HTTPS in production;
- treat this package as one layer in the auth flow, not the whole security model.
