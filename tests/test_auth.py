import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from ecp_lib.auth import (
    authenticate_with_private_key,
    create_challenge,
    create_user_keys,
    read_private_key,
)
from ecp_lib.crypto import generate_keys

from ecp_lib.models import ECPKey


call_command("migrate", run_syncdb=True, verbosity=0)

User = get_user_model()




class TestCreateUserKeys(TestCase):
    def test_stores_public_key_in_db(self):
        # Після виклику в БД має з'явитись запис ECPKey для цього користувача
        user = User.objects.create_user(username="bob", password="secret")
        create_user_keys(user)
        self.assertTrue(ECPKey.objects.filter(user=user).exists())

    def test_returns_private_key_pem(self):
        # Функція повертає private key, який потім віддається користувачу
        user = User.objects.create_user(username="carol", password="secret")
        private_key = create_user_keys(user)
        self.assertIn("PRIVATE KEY", private_key)

    def test_update_or_create_replaces_existing_key(self):
        # Повторний виклик оновлює ключ, а не створює дублікат
        user = User.objects.create_user(username="dave", password="secret")
        create_user_keys(user)
        create_user_keys(user)
        self.assertEqual(ECPKey.objects.filter(user=user).count(), 1)


class TestReadPrivateKey(TestCase):
    def setUp(self):
        self.private_key, _ = generate_keys()

    def test_reads_uploaded_file(self):
        uploaded = SimpleUploadedFile("private.pem", self.private_key.encode("utf-8"))
        result = read_private_key(uploaded)
        self.assertIn("PRIVATE KEY", result)

    def test_rejects_none(self):
        with self.assertRaises(ValueError):
            read_private_key(None)


class TestCreateChallenge(TestCase):
    def test_has_expected_prefix(self):
        challenge = create_challenge()
        self.assertTrue(challenge.startswith("login-test:"))

    def test_unique_each_call(self):
        # Кожен challenge унікальний — захист від replay-атак
        self.assertNotEqual(create_challenge(), create_challenge())


class TestAuthenticateWithPrivateKey(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="alice", password="secret")
        self.private_key, self.public_key = generate_keys()
        ECPKey.objects.create(user=self.user, public_key=self.public_key)

    def test_success(self):
        # Правильні дані повертають користувача без помилки
        user, error = authenticate_with_private_key(
            self.factory.post("/"), "alice", "secret", self.private_key
        )
        self.assertEqual(user, self.user)
        self.assertIsNone(error)

    def test_wrong_password(self):
        user, error = authenticate_with_private_key(
            self.factory.post("/"), "alice", "wrong", self.private_key
        )
        self.assertIsNone(user)
        self.assertIsNotNone(error)

    def test_wrong_private_key(self):
        # Чужий приватний ключ не відповідає збереженому public key
        wrong_key, _ = generate_keys()
        user, error = authenticate_with_private_key(
            self.factory.post("/"), "alice", "secret", wrong_key
        )
        self.assertIsNone(user)
        self.assertEqual(error, "Private key does not match stored public key.")

    def test_user_without_ecp_key(self):
        # Якщо в БД немає ECPKey для користувача — повертаємо помилку
        user = User.objects.create_user(username="nokey", password="secret")
        result_user, error = authenticate_with_private_key(
            self.factory.post("/"), "nokey", "secret", self.private_key
        )
        self.assertIsNone(result_user)
        self.assertEqual(error, "Public key not found for user.")

    def test_invalid_username(self):
        user, error = authenticate_with_private_key(
            self.factory.post("/"), "alice'; DROP TABLE--", "secret", self.private_key
        )
        self.assertIsNone(user)
        self.assertIsNotNone(error)
