
import django
django.setup()

from django.contrib.auth import get_user_model

from django.core.management import call_command
from django.test import TestCase
from ecp_lib.crypto import generate_keys
from ecp_lib.validators import sanitize, validate_public_key, validate_username

call_command("migrate", run_syncdb=True, verbosity=0)

User = get_user_model()


class TestSanitize(TestCase):
    def test_strips_whitespace(self):
        self.assertEqual(sanitize("  hello  "), "hello")

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            sanitize("")

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValueError):
            sanitize("   ")

    def test_rejects_control_characters(self):
        # \x00 — null byte, явно підозрілий у будь-якому полі
        with self.assertRaises(ValueError):
            sanitize("hello\x00world")

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            sanitize(123)

    def test_rejects_too_long_value(self):
        with self.assertRaises(ValueError):
            sanitize("a" * 9000)


class TestValidateUsername(TestCase):
    def test_valid_username(self):
        # Звичайні символи мають проходити без помилок
        self.assertEqual(validate_username("alice"), "alice")

    def test_valid_username_with_special_chars(self):
        self.assertEqual(validate_username("alice.bob@example-1"), "alice.bob@example-1")

    def test_rejects_spaces(self):
        with self.assertRaises(ValueError):
            validate_username("alice bob")

    def test_rejects_injection_attempt(self):
        # SQL/shell-ін'єкційні символи мають відхилятись
        with self.assertRaises(ValueError):
            validate_username("alice'; DROP TABLE users;--")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            validate_username("")


class TestValidatePublicKey(TestCase):
    def setUp(self):
        _, self.public_key = generate_keys()

    def test_valid_public_key(self):
        # Валідний RSA-2048 public key проходить без помилок
        validate_public_key(self.public_key)

    def test_rejects_random_string(self):
        with self.assertRaises(ValueError):
            validate_public_key("not a key")

    def test_rejects_private_key_as_public(self):
        # Приватний ключ не повинен проходити як публічний
        private_key, _ = generate_keys()
        with self.assertRaises(ValueError):
            validate_public_key(private_key)
