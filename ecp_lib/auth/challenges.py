from __future__ import annotations

import base64
import binascii
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from ..core.exceptions import ChallengeValidationError, SignatureVerificationError
from ..core.settings import get_ecp_auth_setting
from ..core.validators import require_mapping, validate_identifier, validate_signature_text
from ..crypto.signatures import verify_signature


@dataclass(frozen=True)
class AuthenticationChallenge:
    challenge: str
    identifier: str
    nonce: str
    expires_in: int
    expires_at: datetime


@dataclass(frozen=True)
class ParsedChallengePayload:
    subject: str
    nonce: str
    issued_at: datetime
    expires_at: datetime


def issue_authentication_challenge(identifier: str) -> AuthenticationChallenge:
    """Create and store a one-time authentication challenge for a user identifier."""
    validated_identifier = validate_identifier(identifier)
    nonce = secrets.token_urlsafe(32)
    ttl_seconds = int(get_ecp_auth_setting("CHALLENGE_TTL_SECONDS"))
    issued_at = timezone.now()
    expires_at = issued_at + timedelta(seconds=ttl_seconds)

    payload = {
        "v": 1,
        "sub": validated_identifier,
        "nonce": nonce,
        "iat": issued_at.isoformat(),
        "exp": expires_at.isoformat(),
    }
    challenge = _encode_payload(payload)

    cache.set(
        _cache_key(nonce),
        {
            "challenge_hash": _hash_text(challenge),
            "identifier": validated_identifier,
        },
        timeout=ttl_seconds,
    )

    return AuthenticationChallenge(
        challenge=challenge,
        identifier=validated_identifier,
        nonce=nonce,
        expires_in=ttl_seconds,
        expires_at=expires_at,
    )


def verify_authentication_response(
    *,
    identifier: str,
    challenge: str,
    signature: str,
    public_key_pem: str,
) -> bool:
    """Verify a signed challenge and invalidate it after successful use."""
    validated_identifier = validate_identifier(identifier)
    validated_signature = validate_signature_text(signature)
    payload = _parse_challenge_payload(challenge)

    if payload.subject != validated_identifier:
        raise ChallengeValidationError(
            "Challenge subject does not match identifier",
            challenge_subject=payload.subject,
            identifier=validated_identifier,
        )

    _validate_challenge_time_window(payload)

    cached_challenge = cache.get(_cache_key(payload.nonce))
    if cached_challenge is None:
        raise ChallengeValidationError(
            "Challenge expired, unknown, or already used",
            nonce=payload.nonce,
        )

    expected_hash = cached_challenge.get("challenge_hash")
    provided_hash = _hash_text(challenge)
    if not isinstance(expected_hash, str) or not compare_digest(expected_hash, provided_hash):
        raise ChallengeValidationError("Challenge payload mismatch for nonce", nonce=payload.nonce)

    cached_identifier = cached_challenge.get("identifier")
    if not isinstance(cached_identifier, str) or not compare_digest(cached_identifier, validated_identifier):
        raise ChallengeValidationError(
            "Challenge identifier mismatch",
            cached_identifier=cached_identifier,
            identifier=validated_identifier,
        )

    if not verify_signature(public_key_pem, challenge, validated_signature):
        raise SignatureVerificationError(
            "Digital signature verification failed",
            nonce=payload.nonce,
            identifier=validated_identifier,
        )

    cache.delete(_cache_key(payload.nonce))
    return True


def _cache_key(nonce: str) -> str:
    prefix = str(get_ecp_auth_setting("CACHE_PREFIX"))
    return f"{prefix}:{nonce}"


def _encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_payload(challenge: str) -> dict[str, Any]:
    if not isinstance(challenge, str) or not challenge.strip():
        raise ChallengeValidationError("Challenge must be a non-empty string")

    try:
        raw = base64.urlsafe_b64decode(challenge.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ChallengeValidationError("Challenge must be URL-safe base64 encoded JSON") from exc

    return require_mapping(data, label="Challenge payload")


def _parse_challenge_payload(challenge: str) -> ParsedChallengePayload:
    payload = _decode_payload(challenge)

    subject = payload.get("sub")
    nonce = payload.get("nonce")
    issued_at_raw = payload.get("iat")
    expires_at_raw = payload.get("exp")

    if not isinstance(subject, str) or not subject:
        raise ChallengeValidationError("Challenge field 'sub' is required")
    if not isinstance(nonce, str) or not nonce:
        raise ChallengeValidationError("Challenge field 'nonce' is required")

    issued_at = _parse_iso_datetime(issued_at_raw, field_name="iat")
    expires_at = _parse_iso_datetime(expires_at_raw, field_name="exp")

    if expires_at <= issued_at:
        raise ChallengeValidationError(
            "Challenge expiration must be after issue time",
            iat=issued_at.isoformat(),
            exp=expires_at.isoformat(),
        )

    return ParsedChallengePayload(
        subject=subject,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _parse_iso_datetime(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ChallengeValidationError(f"Challenge field '{field_name}' is required")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ChallengeValidationError(
            f"Challenge field '{field_name}' must be ISO-8601 datetime"
        ) from exc

    if timezone.is_naive(parsed):
        raise ChallengeValidationError(
            f"Challenge field '{field_name}' must contain timezone info"
        )

    return parsed


def _validate_challenge_time_window(payload: ParsedChallengePayload) -> None:
    now = timezone.now()
    skew = int(get_ecp_auth_setting("CHALLENGE_CLOCK_SKEW_SECONDS"))

    if payload.issued_at > now + timedelta(seconds=skew):
        raise ChallengeValidationError(
            "Challenge issued_at is in the future beyond allowed skew",
            iat=payload.issued_at.isoformat(),
            now=now.isoformat(),
            skew_seconds=skew,
        )

    if payload.expires_at < now - timedelta(seconds=skew):
        raise ChallengeValidationError(
            "Challenge has expired",
            exp=payload.expires_at.isoformat(),
            now=now.isoformat(),
            skew_seconds=skew,
        )


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
