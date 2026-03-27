# ecp-lib

<<<<<<< HEAD
`ecp-lib` is a Django-oriented package for RSA key generation, public key storage, login helpers, and request validation middleware.

The package covers two related concerns:

- generating an RSA key pair for a user and storing only the public key on the server;
- validating login-like requests that carry `username`, `password`, and a private key field or upload.

It does not provide ready-made views, forms, URLs, or session login flow.

=======
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

>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894
## Installation

```bash
pip install ecp-lib
pip install "ecp-lib[django]"
```

<<<<<<< HEAD
Base dependency:

- `cryptography>=46.0.6`

Optional Django extra:

- `django>=4.2,<6.0`

=======
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894
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

<<<<<<< HEAD
The root package uses lazy imports, so it is safe to include in `INSTALLED_APPS` without importing models too early.
=======
The main Django-flow uses:
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

## Main Django flow

<<<<<<< HEAD
### 1. Registration

After creating a user, call `create_user_keys(user)`.

What it does:

1. Generates a new RSA key pair.
2. Validates the generated public key.
3. Stores the public key in `ECPKey`.
4. Returns the private key PEM string so the view can return it to the user.

Example:
=======
## Main flow

### 1. Registration

After creating a user, call `create_user_keys(user)`.
The function:

1. generates a new RSA key pair
2. stores the `public_key` in `ECPKey`
3. returns the `private_key` as a PEM string

Typical approach: provide this PEM to the user as a `private.pem` file.
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

```python
from django.http import HttpResponse

from ecp_lib.auth import create_user_keys


def registration_success(request, user):
    private_key = create_user_keys(user)

    response = HttpResponse(private_key, content_type="application/x-pem-file")
    response["Content-Disposition"] = 'attachment; filename="private.pem"'
    return response
```

<<<<<<< HEAD
### 2. Login helper

In your login view, read the uploaded PEM and pass it to `authenticate_with_private_key(...)`.
=======
### 2. Login

The login form submits:

- `username`
- `password`
- a `private_key` or `private_key_file`

In the view, you can read the PEM and verify it using the helper:
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

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

<<<<<<< HEAD
1. Validates `username`, `password`, and `private_key`.
2. Calls Django `authenticate(...)`.
3. Reads the user's stored `public_key` from `ECPKey`.
4. Creates a one-time challenge string.
5. Signs that challenge with the provided private key.
6. Verifies the signature with the stored public key.

Return value:

- `(user, None)` on success;
- `(None, "error message")` on failure.

## Middleware

`ECPMiddleware` is an early request validator for `POST` requests.

It runs only when the request contains at least one ECP-related field:

- `username`
- `password`
- `private_key`
- `private_key_file`
- `key_file`

Supported payload types:
=======
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
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

- `application/x-www-form-urlencoded`
- `multipart/form-data`
- `application/json`

<<<<<<< HEAD
What the middleware does:

1. Skips all non-`POST` requests.
2. Extracts request payload from `POST` data or JSON body.
3. Detects whether the request looks like an ECP-related request.
4. Validates `username`.
5. Validates `password`.
6. Reads a private key from text field or uploaded file if present.
7. Sanitizes the private key value.
8. Returns `400` with JSON errors if validation fails.
9. Passes the request through untouched if validation succeeds.

Important behavior:

- middleware does not authenticate the user;
- middleware does not call Django `login()`;
- middleware does not compare the private key against the stored public key;
- middleware resets uploaded file pointer with `seek(0)` after reading, so the view can read the file again.

Example error response:

```json
{
  "detail": "Invalid request.",
  "errors": [
    "username: Username contains unsupported characters."
  ]
}
```

## Django integration

=======
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

>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894
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

<<<<<<< HEAD
Then run migrations:
=======
After that, run the migrations:
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

```bash
python manage.py migrate
```

<<<<<<< HEAD
## Logging

Middleware logs through `ecp_lib.middleware`.
=======
## Middleware Logging

To see if the middleware is triggered, add a logger in `settings.py`:
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

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

<<<<<<< HEAD
## Low-level helpers
=======
The logs will show:

- that the request reached the middleware
- why the middleware allowed the request
- why the middleware rejected the request
- whether the verification succeeded

## Cryptographic Helpers
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

### `generate_keys()`

```python
from ecp_lib.crypto import generate_keys

private_key, public_key = generate_keys()
```

<<<<<<< HEAD
Behavior:

- generates an RSA key pair;
- returns two PEM strings;
- rejects key sizes smaller than `2048`.

### `sign()` and `verify()`
=======
- returns PEM strings
- generates only RSA keys
- minimum key length: `2048`

### `sign()` & `verify()`
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

```python
from ecp_lib.crypto import sign, verify

signature = sign(private_key, "hello")
is_valid = verify(public_key, "hello", signature)
```

<<<<<<< HEAD
Implementation details:

- RSA-PSS
- SHA-256
- base64-encoded signature

### `create_challenge()`

```python
from ecp_lib.auth import create_challenge

challenge = create_challenge()
```

Returns a unique login challenge string with the prefix `login-test:`.

### `read_private_key()`

Reads an uploaded Django file, decodes it as UTF-8, sanitizes it, and returns the PEM text.

## Validation

`ecp_lib.validators` currently exports:
=======
The library uses `RSA-PSS` with `SHA-256`.

### `create_challenge()` & `verify_challenge()`

These are auxiliary helpers for testing or local verification of key pairs.
They are not part of the main login flow via the HTML form.

## Validation

[`ecp_lib/validators.py`](/home/toksik/Developer/hackaton/django-pub-sub/ecp_lib/validators.py) contains:
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

- `sanitize(value)`
- `validate_username(username)`
- `validate_public_key(public_key)`

<<<<<<< HEAD
What is validated:

- string type and non-empty value;
- maximum input length;
- control characters in raw input;
- username allowed character set;
- PEM structure of the public key;
- RSA key type and minimum size `2048`.

## Data model
=======
It validates:

- the type and non-emptiness of the value
- absence of dangerous control characters
- PEM format of the `public_key`
- RSA key type
- minimum key length of `2048`

## Model
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

`ECPKey` stores:

- `user` as `OneToOneField`;
- `public_key` as `TextField`;
- `created_at` as `DateTimeField(auto_now_add=True)`.

<<<<<<< HEAD
Only the public key is stored on the server.
=======
Only the `public_key` is stored on the server.
>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894

## Tests

Run:

```bash
pytest -q
```

<<<<<<< HEAD
Current test coverage includes:

- RSA key generation;
- signing and signature verification;
- public key validation;
- username and input sanitization;
- creation and replacement of `ECPKey`;
- reading uploaded private keys;
- login helper behavior;
- middleware behavior for form uploads and validation failures.

## Limitations

- no built-in views, forms, or URL routes;
- no challenge-response session protocol beyond the in-memory helper check;
- no replay protection storage or server-side nonce tracking;
- middleware validates request shape only and is not a replacement for authentication logic in the view.

## Security notes

- never store `private.pem` on the server;
- return the private key to the user only at the moment you create it;
- use HTTPS because password and private key travel to the server;
- keep the middleware as an early input-validation layer, not as the only authentication check.
=======
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

>>>>>>> 5e8bfa73c0fc076fcbee372bc58cdd2d87fbe894
