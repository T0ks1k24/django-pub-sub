from __future__ import annotations

import base64
import json
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

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from ecp_lib.auth.challenges import issue_authentication_challenge, verify_authentication_response
from ecp_lib.core.exceptions import ChallengeValidationError, SignatureVerificationError
from ecp_lib.crypto import generate_rsa_key_pair, sign_payload


class ChallengeTests(SimpleTestCase):
    def setUp(self) -> None:
        cache.clear()
        self.private_key, self.public_key = generate_rsa_key_pair()
        self.identifier = "alice"

    def test_issue_and_verify_valid_challenge(self) -> None:
        challenge = issue_authentication_challenge(self.identifier)
        signature = sign_payload(self.private_key, challenge.challenge)

        result = verify_authentication_response(
            identifier=self.identifier,
            challenge=challenge.challenge,
            signature=signature,
            public_key_pem=self.public_key,
        )

        self.assertTrue(result)

    def test_replay_is_rejected_after_successful_verification(self) -> None:
        challenge = issue_authentication_challenge(self.identifier)
        signature = sign_payload(self.private_key, challenge.challenge)

        verify_authentication_response(
            identifier=self.identifier,
            challenge=challenge.challenge,
            signature=signature,
            public_key_pem=self.public_key,
        )

        with self.assertRaises(ChallengeValidationError) as context:
            verify_authentication_response(
                identifier=self.identifier,
                challenge=challenge.challenge,
                signature=signature,
                public_key_pem=self.public_key,
            )

        self.assertIn("already used", str(context.exception))

    def test_subject_mismatch_is_rejected(self) -> None:
        challenge = issue_authentication_challenge(self.identifier)
        signature = sign_payload(self.private_key, challenge.challenge)

        with self.assertRaises(ChallengeValidationError) as context:
            verify_authentication_response(
                identifier="bob",
                challenge=challenge.challenge,
                signature=signature,
                public_key_pem=self.public_key,
            )

        self.assertIn("subject", str(context.exception))
        self.assertEqual(context.exception.details["challenge_subject"], self.identifier)

    def test_invalid_signature_raises_signature_error(self) -> None:
        challenge = issue_authentication_challenge(self.identifier)

        with self.assertRaises(SignatureVerificationError) as context:
            verify_authentication_response(
                identifier=self.identifier,
                challenge=challenge.challenge,
                signature="invalid-signature",
                public_key_pem=self.public_key,
            )

        self.assertEqual(context.exception.code, "signature_verification_error")

    @override_settings(ECP_AUTH={"MAX_SIGNATURE_LENGTH": 10})
    def test_signature_length_is_validated(self) -> None:
        challenge = issue_authentication_challenge(self.identifier)

        with self.assertRaises(ChallengeValidationError) as context:
            verify_authentication_response(
                identifier=self.identifier,
                challenge=challenge.challenge,
                signature="x" * 11,
                public_key_pem=self.public_key,
            )

        self.assertIn("maximum allowed length", str(context.exception))

    def test_invalid_challenge_format_is_rejected(self) -> None:
        with self.assertRaises(ChallengeValidationError) as context:
            verify_authentication_response(
                identifier=self.identifier,
                challenge="not-base64",
                signature="abcd",
                public_key_pem=self.public_key,
            )

        self.assertIn("base64", str(context.exception))

    def test_missing_required_field_in_payload_is_rejected(self) -> None:
        payload = {
            "sub": self.identifier,
            "nonce": "nonce",
            "iat": timezone.now().isoformat(),
            # exp is intentionally missing
        }
        challenge = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).decode("ascii")

        with self.assertRaises(ChallengeValidationError) as context:
            verify_authentication_response(
                identifier=self.identifier,
                challenge=challenge,
                signature="abcd",
                public_key_pem=self.public_key,
            )

        self.assertIn("field 'exp'", str(context.exception))
