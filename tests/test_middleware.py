import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase


from ecp_lib.crypto import generate_keys
from ecp_lib.middleware import ECPMiddleware
from ecp_lib.models import ECPKey

User = get_user_model()

class TestECPMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ECPMiddleware(lambda r: HttpResponse("ok"))
        self.user = User.objects.create_user(username="alice", password="secret")
        self.private_key, self.public_key = generate_keys()
        ECPKey.objects.update_or_create(user=self.user, defaults={"public_key": self.public_key})

    def test_passes_non_post_request(self):
        # GET-запити middleware не чіпає взагалі
        request = self.factory.get("/")
        self.assertEqual(self.middleware(request).status_code, 200)

    def test_passes_post_without_ecp_fields(self):
        # POST без ECP-полів — не наш запит, пропускаємо
        request = self.factory.post("/", data={"some_field": "value"})
        self.assertEqual(self.middleware(request).status_code, 200)

    def test_passes_valid_form_data(self):
        uploaded = SimpleUploadedFile("key.pem", self.private_key.encode("utf-8"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice", "password": "secret", "key_file": uploaded},
        )
        self.assertEqual(self.middleware(request).status_code, 200)

    def test_rejects_invalid_username(self):
        uploaded = SimpleUploadedFile("key.pem", self.private_key.encode("utf-8"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice '; DROP--", "password": "secret", "key_file": uploaded},
        )
        self.assertEqual(self.middleware(request).status_code, 400)

    def test_rejects_empty_password(self):
        uploaded = SimpleUploadedFile("key.pem", self.private_key.encode("utf-8"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice", "password": "", "key_file": uploaded},
        )
        self.assertEqual(self.middleware(request).status_code, 400)

    def test_file_seeked_after_read(self):
        # Middleware має зробити seek(0) щоб view міг прочитати файл ще раз
        uploaded = SimpleUploadedFile("key.pem", self.private_key.encode("utf-8"))
        request = self.factory.post(
            "/login/",
            data={"username": "alice", "password": "secret", "key_file": uploaded},
        )
        self.middleware(request)
        self.assertEqual(request.FILES["key_file"].read(), self.private_key.encode("utf-8"))