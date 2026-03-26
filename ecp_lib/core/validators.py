from __future__ import annotations

import re
from typing import Any

from .exceptions import ChallengeValidationError, ValidationError
from .settings import get_ecp_auth_setting


def validate_identifier(identifier: str) -> str:
    """Validate identifier format used for user lookup and challenge subject."""
    if not isinstance(identifier, str):
        raise ValidationError(
            "Identifier must be a string",
            expected_type="str",
            received_type=type(identifier).__name__,
        )

    value = identifier.strip()
    if not value:
        raise ValidationError("Identifier cannot be empty")

    max_length = int(get_ecp_auth_setting("IDENTIFIER_MAX_LENGTH"))
    if len(value) > max_length:
        raise ValidationError(
            "Identifier exceeds maximum length",
            max_length=max_length,
            current_length=len(value),
        )

    pattern = str(get_ecp_auth_setting("ALLOWED_IDENTIFIER_CHARS"))
    if not re.fullmatch(pattern, value):
        raise ValidationError(
            "Identifier contains unsupported characters",
            pattern=pattern,
            identifier=value,
        )

    return value


def validate_signature_text(signature: str) -> str:
    """Validate serialized signature before cryptographic verification."""
    if not isinstance(signature, str):
        raise ChallengeValidationError(
            "Signature must be a string",
            expected_type="str",
            received_type=type(signature).__name__,
        )

    signature = signature.strip()
    if not signature:
        raise ChallengeValidationError("Signature cannot be empty")

    max_length = int(get_ecp_auth_setting("MAX_SIGNATURE_LENGTH"))
    if len(signature) > max_length:
        raise ChallengeValidationError(
            "Signature exceeds maximum allowed length",
            max_length=max_length,
            current_length=len(signature),
        )

    return signature


def require_mapping(payload: Any, *, label: str) -> dict[str, Any]:
    """Ensure a parsed payload is a dictionary-like mapping."""
    if not isinstance(payload, dict):
        raise ChallengeValidationError(
            f"{label} must be a JSON object",
            received_type=type(payload).__name__,
        )
    return payload
