from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "ecp_lib",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        USE_TZ=True,
    )

import django

django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.http import HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from ecp_lib.auth import (
    authenticate_with_private_key,
    create_challenge,
    create_user_keys,
    read_private_key,
    verify_challenge,
)
from ecp_lib.crypto import generate_keys, sign, verify
from ecp_lib.middleware import ECPMiddleware
from ecp_lib.models import ECPKey
from ecp_lib.validators import sanitize, validate_public_key

call_command("migrate", run_syncdb=True, verbosity=0)


class ECPLibTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="alice", password="secret")
        self.private_key, self.public_key = generate_keys()
        ECPKey.objects.create(user=self.user, public_key=self.public_key)

    def test_generate_sign_verify(self) -> None:
        signature = sign(self.private_key, "hello")
        self.assertTrue(verify(self.public_key, "hello", signature))

    def test_create_user_keys_stores_public_key(self) -> None:
        user = get_user_model().objects.create_user(username="bob", password="secret")

        private_key = create_user_keys(user)

        self.assertIn("PRIVATE KEY", private_key)
        self.assertTrue(ECPKey.objects.filter(user=user).exists())

    def test_create_challenge_returns_non_empty_string(self) -> None:
        challenge = create_challenge()
        self.assertTrue(challenge.startswith("login-test:"))

    def test_verify_challenge_for_matching_keys(self) -> None:
        self.assertTrue(verify_challenge(self.private_key, self.public_key, create_challenge()))

    def test_read_private_key_from_uploaded_file(self) -> None:
        uploaded_file = SimpleUploadedFile("private.pem", self.private_key.encode("utf-8"))

        result = read_private_key(uploaded_file)

        self.assertIn("PRIVATE KEY", result)

    def test_authenticate_with_private_key_success(self) -> None:
        request = self.factory.post("/login/")

        user, error = authenticate_with_private_key(
            request=request,
            username="alice",
            password="secret",
            private_key=self.private_key,
        )

        self.assertEqual(user, self.user)
        self.assertIsNone(error)

    def test_authenticate_with_private_key_returns_error_for_wrong_key(self) -> None:
        wrong_private_key, _ = generate_keys()
        request = self.factory.post("/login/")

        user, error = authenticate_with_private_key(
            request=request,
            username="alice",
            password="secret",
            private_key=wrong_private_key,
        )

        self.assertIsNone(user)
        self.assertEqual(error, "Private key does not match stored public key.")

    def test_validate_public_key(self) -> None:
        validate_public_key(self.public_key)
        with self.assertRaises(ValueError):
            validate_public_key("bad key")

    def test_middleware_blocks_bad_signature(self) -> None:
        middleware = ECPMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice", "signature": "bad", "challenge": "hello"},
        )

        response = middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_middleware_passes_valid_signature(self) -> None:
        signature = sign(self.private_key, "hello")
        middleware = ECPMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice", "signature": signature, "challenge": "hello"},
        )

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_sanitize_rejects_empty_value(self) -> None:
        with self.assertRaises(ValueError):
            sanitize("   ")
