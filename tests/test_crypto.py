
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command

from django.test import TestCase


from ecp_lib.crypto import generate_keys, sign, verify


call_command("migrate", run_syncdb=True, verbosity=0)

User = get_user_model()




class TestGenerateKeys(TestCase):
    def test_returns_pem_strings(self):
        # generate_keys() має повертати два PEM-рядки
        private_key, public_key = generate_keys()
        self.assertIn("PRIVATE KEY", private_key)
        self.assertIn("PUBLIC KEY", public_key)

    def test_keys_are_unique(self):
        # Кожен виклик генерує нову пару — ключі не повторюються
        private_key_1, _ = generate_keys()
        private_key_2, _ = generate_keys()
        self.assertNotEqual(private_key_1, private_key_2)

    def test_rejects_small_key_size(self):
        # Ключі коротші за 2048 біт відхиляються як небезпечні
        with self.assertRaises(ValueError):
            generate_keys(key_size=1024)


class TestSignVerify(TestCase):
    def setUp(self):
        self.private_key, self.public_key = generate_keys()

    def test_valid_signature(self):
        # Підпис створений правильним ключем має проходити перевірку
        signature = sign(self.private_key, "hello")
        self.assertTrue(verify(self.public_key, "hello", signature))

    def test_wrong_payload(self):
        # Підпис від одного payload не підходить для іншого
        signature = sign(self.private_key, "hello")
        self.assertFalse(verify(self.public_key, "world", signature))

    def test_wrong_public_key(self):
        # Підпис не проходить перевірку чужим public key
        _, other_public_key = generate_keys()
        signature = sign(self.private_key, "hello")
        self.assertFalse(verify(other_public_key, "hello", signature))

    def test_corrupted_signature(self):
        # Пошкоджений base64 підпис повертає False, а не кидає виняток
        self.assertFalse(verify(self.public_key, "hello", "not-a-valid-base64!!!"))

    def test_sign_rejects_invalid_private_key(self):
        # sign() кидає ValueError якщо передати не-PEM рядок
        with self.assertRaises(ValueError):
            sign("not a key", "hello")