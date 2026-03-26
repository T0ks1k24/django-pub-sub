# ecp-lib Package Guide

## Overview

`ecp-lib` is a reusable Python library for RSA signatures with optional Django backend integration.

The canonical import namespace is `ecp_lib`.

Main capabilities:
- RSA key generation and validation.
- Payload signing and signature verification.
- One-time challenge-response flow for EЦП authentication.
- Django `AuthenticationBackend` integration.
- CLI for operational tasks.

## Module Structure

- `ecp_lib.auth`
  - `backend.py`: `ECPAuthenticationBackend`
  - `challenges.py`: challenge issue/verification and anti-replay
- `ecp_lib.crypto`
  - `keys.py`: key generation and pair validation
  - `signatures.py`: sign/verify primitives
- `ecp_lib.core`
  - `exceptions.py`: structured exceptions with error code and details
  - `settings.py`: ECP settings adapter
  - `validators.py`: input validation
- `ecp_lib.cli`
  - `main(argv=None)`: console entry point used by `ecp-lib`

## Installation

Core library:

```bash
pip install ecp-lib
```

With Django integration:

```bash
pip install "ecp-lib[django]"
```

For editable development:

```bash
pip install -e .
```

## Django Configuration

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

Зв'язок ключа з користувачем:
- `ecp_lib.models.ECPUserPublicKey`
- `user`: `OneToOneField(settings.AUTH_USER_MODEL)`
- `public_key`: `TextField()`

## Python API Quick Examples

```python
from ecp_lib import generate_rsa_key_pair, sign_payload, verify_signature

private_key, public_key = generate_rsa_key_pair()
signature = sign_payload(private_key, "challenge")
assert verify_signature(public_key, "challenge", signature)
```

```python
from ecp_lib import issue_authentication_challenge, verify_authentication_response

challenge = issue_authentication_challenge("alice")
# client signs challenge.challenge
# verify_authentication_response(...) on server side
```

## CLI Entry Point

After installation, CLI command is available as:

```bash
ecp-lib --help
```

Module form is also available:

```bash
python -m ecp_lib.cli --help
```

Commands:
- `ecp-lib generate-keys [--key-size 2048] [--format pem|json]`
- `ecp-lib validate-keys --private-key-file <path> --public-key-file <path>`
- `ecp-lib sign --private-key-file <path> (--payload <text> | --payload-file <path>)`
- `ecp-lib verify --public-key-file <path> --signature <base64> (--payload <text> | --payload-file <path>)`

Exit codes:
- `0`: success
- `1`: verification failed (`verify` command)
- `2`: input/validation/runtime error

Typical flow:

```bash
ecp-lib generate-keys --format json
ecp-lib sign --private-key-file private.pem --payload "hello"
ecp-lib verify --public-key-file public.pem --payload "hello" --signature "<base64>"
```

## Error Handling

Domain-level exceptions derive from `ECPError` and include:
- `code`: machine-readable error code
- `details`: structured context for debugging

This allows detailed diagnostics for developers while keeping business logic explicit.
