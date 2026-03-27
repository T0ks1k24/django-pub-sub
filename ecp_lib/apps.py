"""Django app configuration for the ECP library."""

from django.apps import AppConfig


class EcpLibConfig(AppConfig):
    """Application config for registering the ECP app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ecp_lib"
