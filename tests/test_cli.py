from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from ecp_lib.cli import main
from ecp_lib.crypto import generate_rsa_key_pair


class CLITests(unittest.TestCase):
    def test_generate_keys_json_output(self) -> None:
        stdout_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer):
            exit_code = main(["generate-keys", "--format", "json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout_buffer.getvalue())
        self.assertIn("private_key", payload)
        self.assertIn("public_key", payload)

    def test_sign_and_verify_success(self) -> None:
        private_key, public_key = generate_rsa_key_pair()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            private_key_file = tmp_path / "private.pem"
            public_key_file = tmp_path / "public.pem"
            private_key_file.write_text(private_key, encoding="utf-8")
            public_key_file.write_text(public_key, encoding="utf-8")

            sign_out = io.StringIO()
            with redirect_stdout(sign_out):
                sign_code = main(
                    [
                        "sign",
                        "--private-key-file",
                        str(private_key_file),
                        "--payload",
                        "hello",
                    ]
                )
            signature = sign_out.getvalue().strip()

            verify_out = io.StringIO()
            with redirect_stdout(verify_out):
                verify_code = main(
                    [
                        "verify",
                        "--public-key-file",
                        str(public_key_file),
                        "--payload",
                        "hello",
                        "--signature",
                        signature,
                    ]
                )

        self.assertEqual(sign_code, 0)
        self.assertEqual(verify_code, 0)
        self.assertEqual(verify_out.getvalue().strip(), "VALID")

    def test_verify_invalid_signature_returns_non_zero(self) -> None:
        _, public_key = generate_rsa_key_pair()

        with tempfile.TemporaryDirectory() as tmp_dir:
            public_key_file = Path(tmp_dir) / "public.pem"
            public_key_file.write_text(public_key, encoding="utf-8")

            verify_out = io.StringIO()
            with redirect_stdout(verify_out):
                exit_code = main(
                    [
                        "verify",
                        "--public-key-file",
                        str(public_key_file),
                        "--payload",
                        "hello",
                        "--signature",
                        "bad-signature",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(verify_out.getvalue().strip(), "INVALID")

    def test_missing_file_returns_input_error(self) -> None:
        stderr_buffer = io.StringIO()

        with redirect_stderr(stderr_buffer):
            exit_code = main(
                [
                    "validate-keys",
                    "--private-key-file",
                    "missing-private.pem",
                    "--public-key-file",
                    "missing-public.pem",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("Input error", stderr_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
