from setuptools import setup, find_packages

setup(
    name='ecp-lib',
    version="0.1.0",
    packages=find_packages(include=["ecp_lib", "ecp_lib.*"]),
    install_requires=[
        'cryptography>=46.0.6',
    ],
    extras_require={
        "django": [
            'django>=4.2,<6.0',
        ],
    },
)
