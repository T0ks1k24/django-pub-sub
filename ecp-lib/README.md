# ecp-lib

`ecp-lib` is a small Python package for RSA key pair generation and key pair validation.

## Installation

```bash
pip install ecp-lib
```

For local development:

```bash
pip install -e .
```

## Usage

### Generate key pair

```python
from ecp_lib import generate_rsa_key_pair

private_key_pem, public_key_pem = generate_rsa_key_pair()
print(private_key_pem)
print(public_key_pem)
```

### Validate key pair

```python
from ecp_lib import validate_rsa_keys

is_valid = validate_rsa_keys(private_key_pem, public_key_pem)
print(is_valid)  # True
```

### Backward-compatible wrapper

```python
from ecp_lib import generating_rsa_keys

text_output = generating_rsa_keys()
print(text_output)
```

## Development quick check

```bash
python -c "from ecp_lib import generate_rsa_key_pair, validate_rsa_keys; pvt, pub = generate_rsa_key_pair(); print(validate_rsa_keys(pvt, pub))"
```

Expected output:

```text
True
```
