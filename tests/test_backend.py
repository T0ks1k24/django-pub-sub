from __future__ import annotations

from dataclasses import dataclass
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

from ecp_lib.auth.backend import ECPAuthenticationBackend
from ecp_lib.auth.challenges import issue_authentication_challenge
from ecp_lib.crypto import generate_rsa_key_pair, sign_payload


@dataclass
class DummyProfile:
    public_key: str


@dataclass
class DummyUser:
    username: str
    public_key: str | None = None
    profile: DummyProfile | None = None
    is_active: bool = True


class BackendTests(SimpleTestCase):
    def setUp(self) -> None:
        cache.clear()
        self.private_key, self.public_key = generate_rsa_key_pair()
        self.backend = ECPAuthenticationBackend()
        self.user = DummyUser(username="alice", public_key=self.public_key)

    def test_authenticate_returns_user_for_valid_signature(self) -> None:
        challenge = issue_authentication_challenge(self.user.username)
        signature = sign_payload(self.private_key, challenge.challenge)

        authenticated_user = self.backend.authenticate(
            request=None,
            user=self.user,
            identifier=self.user.username,
            challenge=challenge.challenge,
            signature=signature,
        )

        self.assertIs(authenticated_user, self.user)

    def test_authenticate_rejects_invalid_signature(self) -> None:
        challenge = issue_authentication_challenge(self.user.username)

        authenticated_user = self.backend.authenticate(
            request=None,
            user=self.user,
            identifier=self.user.username,
            challenge=challenge.challenge,
            signature="invalid-signature",
        )

        self.assertIsNone(authenticated_user)

    def test_authenticate_rejects_inactive_user(self) -> None:
        inactive_user = DummyUser(
            username="alice",
            public_key=self.public_key,
            is_active=False,
        )
        challenge = issue_authentication_challenge(inactive_user.username)
        signature = sign_payload(self.private_key, challenge.challenge)

        authenticated_user = self.backend.authenticate(
            request=None,
            user=inactive_user,
            identifier=inactive_user.username,
            challenge=challenge.challenge,
            signature=signature,
        )

        self.assertIsNone(authenticated_user)

    def test_authenticate_rejects_missing_public_key(self) -> None:
        challenge = issue_authentication_challenge(self.user.username)
        signature = sign_payload(self.private_key, challenge.challenge)
        user_without_key = DummyUser(username="alice", public_key=None)

        authenticated_user = self.backend.authenticate(
            request=None,
            user=user_without_key,
            identifier=user_without_key.username,
            challenge=challenge.challenge,
            signature=signature,
        )

        self.assertIsNone(authenticated_user)

    @override_settings(
        ECP_AUTH={
            "PUBLIC_KEY_FIELD": "profile.public_key",
            "USER_LOOKUP_FIELD": "username",
        }
    )
    def test_authenticate_supports_nested_public_key_field(self) -> None:
        user = DummyUser(username="alice", profile=DummyProfile(public_key=self.public_key))
        challenge = issue_authentication_challenge(user.username)
        signature = sign_payload(self.private_key, challenge.challenge)

        authenticated_user = self.backend.authenticate(
            request=None,
            user=user,
            challenge=challenge.challenge,
            signature=signature,
        )

        self.assertIs(authenticated_user, user)

    def test_authenticate_rejects_missing_input(self) -> None:
        self.assertIsNone(self.backend.authenticate(request=None, user=self.user, signature=None, challenge="x"))
        self.assertIsNone(self.backend.authenticate(request=None, user=self.user, signature="x", challenge=None))
