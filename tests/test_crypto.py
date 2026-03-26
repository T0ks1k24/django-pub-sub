from __future__ import annotations

from pathlib import Path
import sys

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
        ],
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "ecp-lib-tests",
            }
        },
        USE_TZ=True,
    )

import django

django.setup()

from django.test import SimpleTestCase

from ecp_lib.core.exceptions import KeyValidationError
from ecp_lib.crypto import (
    generate_rsa_key_pair,
    generating_rsa_keys,
    sign_payload,
    validate_rsa_keys,
    verify_signature,
)


class CryptoTests(SimpleTestCase):
    def test_sign_and_verify_round_trip(self) -> None:
        private_key, public_key = generate_rsa_key_pair()
        signature = sign_payload(private_key, "challenge")

        self.assertTrue(verify_signature(public_key, "challenge", signature))

    def test_verify_fails_for_invalid_base64_signature(self) -> None:
        _, public_key = generate_rsa_key_pair()

        self.assertFalse(verify_signature(public_key, "challenge", "%%not-base64%%"))

    def test_validate_keys_rejects_mismatched_pair(self) -> None:
        private_key_1, _ = generate_rsa_key_pair()
        _, public_key_2 = generate_rsa_key_pair()

        with self.assertRaises(KeyValidationError) as context:
            validate_rsa_keys(private_key_1, public_key_2)

        self.assertEqual(context.exception.code, "key_validation_error")
        self.assertIn("valid pair", str(context.exception))

    def test_generate_rsa_key_pair_rejects_small_key_size(self) -> None:
        with self.assertRaises(KeyValidationError) as context:
            generate_rsa_key_pair(key_size=1024)

        self.assertEqual(context.exception.code, "key_validation_error")
        self.assertEqual(context.exception.details["key_size"], 1024)

    def test_generating_rsa_keys_compatibility_output(self) -> None:
        output = generating_rsa_keys()

        self.assertIn("Private:\n", output)
        self.assertIn("\nPublic:\n", output)
