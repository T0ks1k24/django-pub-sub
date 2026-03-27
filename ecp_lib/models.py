from __future__ import annotations

from django.conf import settings
from django.db import models


class ECPKey(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ecp_key",
    )
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ECP key"
        verbose_name_plural = "ECP keys"

    def __str__(self) -> str:
        return f"ECP key for user_id={self.user_id}"
