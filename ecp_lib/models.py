"""Database models for storing user ECP public keys."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class ECPKey(models.Model):
    """Store the public ECP key associated with a single Django user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ecp_key",
    )
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:  # pylint: disable=too-few-public-methods
        """Model metadata for Django admin and migrations."""

        verbose_name = "ECP key"
        verbose_name_plural = "ECP keys"

    def __str__(self) -> str:
        """Return a compact description for logs and admin screens."""
        return f"ECP key for user_id={self.user_id}"  # pylint: disable=no-member
