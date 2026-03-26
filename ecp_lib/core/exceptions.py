from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorContext:
    """Structured details attached to domain exceptions for diagnostics."""

    code: str
    details: dict[str, Any]


class ECPError(Exception):
    """Base exception for ECP authentication and cryptography flows."""

    default_code = "ecp_error"

    def __init__(self, message: str, *, code: str | None = None, **details: Any) -> None:
        self.message = message
        self.context = ErrorContext(code=code or self.default_code, details=details)
        super().__init__(message)

    @property
    def code(self) -> str:
        return self.context.code

    @property
    def details(self) -> dict[str, Any]:
        return self.context.details

    def __str__(self) -> str:
        if not self.details:
            return f"[{self.code}] {self.message}"
        return f"[{self.code}] {self.message} | details={self.details}"


class ECPAuthenticationError(ECPError):
    default_code = "authentication_error"


class ValidationError(ECPError):
    default_code = "validation_error"


class KeyValidationError(ValidationError):
    default_code = "key_validation_error"


class ChallengeValidationError(ECPAuthenticationError):
    default_code = "challenge_validation_error"


class SignatureVerificationError(ECPAuthenticationError):
    default_code = "signature_verification_error"
