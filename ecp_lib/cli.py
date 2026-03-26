from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core.exceptions import ECPError
from .crypto import generate_rsa_key_pair, sign_payload, validate_rsa_keys, verify_signature


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        return args.handler(args)
    except FileNotFoundError as exc:
        print(f"Input error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    except (OSError, ValueError, ECPError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecp-lib",
        description="RSA/ECP utilities with Django authentication helpers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate-keys", help="Generate an RSA key pair.")
    generate_parser.add_argument("--key-size", type=int, default=2048)
    generate_parser.add_argument("--format", choices=("pem", "json"), default="pem")
    generate_parser.set_defaults(handler=_handle_generate_keys)

    validate_parser = subparsers.add_parser("validate-keys", help="Validate that two PEM keys match.")
    validate_parser.add_argument("--private-key-file", required=True)
    validate_parser.add_argument("--public-key-file", required=True)
    validate_parser.set_defaults(handler=_handle_validate_keys)

    sign_parser = subparsers.add_parser("sign", help="Sign a payload with a private key.")
    sign_parser.add_argument("--private-key-file", required=True)
    _add_payload_arguments(sign_parser)
    sign_parser.set_defaults(handler=_handle_sign)

    verify_parser = subparsers.add_parser("verify", help="Verify a payload signature with a public key.")
    verify_parser.add_argument("--public-key-file", required=True)
    verify_parser.add_argument("--signature", required=True)
    _add_payload_arguments(verify_parser)
    verify_parser.set_defaults(handler=_handle_verify)

    return parser


def _add_payload_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--payload")
    group.add_argument("--payload-file")


def _handle_generate_keys(args: argparse.Namespace) -> int:
    private_key, public_key = generate_rsa_key_pair(key_size=args.key_size)

    if args.format == "json":
        print(
            json.dumps(
                {"private_key": private_key, "public_key": public_key},
                ensure_ascii=False,
            )
        )
    else:
        print(private_key, end="")
        if not private_key.endswith("\n"):
            print()
        print(public_key, end="")
        if not public_key.endswith("\n"):
            print()

    return 0


def _handle_validate_keys(args: argparse.Namespace) -> int:
    private_key = _read_text(args.private_key_file)
    public_key = _read_text(args.public_key_file)
    validate_rsa_keys(private_key, public_key)
    print("VALID")
    return 0


def _handle_sign(args: argparse.Namespace) -> int:
    private_key = _read_text(args.private_key_file)
    payload = _read_payload(args)
    print(sign_payload(private_key, payload))
    return 0


def _handle_verify(args: argparse.Namespace) -> int:
    public_key = _read_text(args.public_key_file)
    payload = _read_payload(args)
    is_valid = verify_signature(public_key, payload, args.signature)
    print("VALID" if is_valid else "INVALID")
    return 0 if is_valid else 1


def _read_payload(args: argparse.Namespace) -> str:
    if args.payload is not None:
        return args.payload
    return _read_text(args.payload_file)


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
