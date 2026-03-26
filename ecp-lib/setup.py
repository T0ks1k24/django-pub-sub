from setuptools import setup, find_packages

setup(
    name='ecp-lib',
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'cryptography>=46.0.6',
        'pycryptodome>=3.23.0',
        'asn1crypto>=1.5.1',
        'certvalidator>=0.11.1'

    ]
)
