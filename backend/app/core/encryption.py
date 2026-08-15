"""Symmetric encryption for integration credentials at rest.

Key is derived from JWT_SECRET so no extra environment variable is
required in development, but in production JWT_SECRET is already
required to be a long random value (see config.validate_production_safety),
so this derivation is safe. Uses Fernet (AES-128-CBC + HMAC), which is
already a transitive dependency via python-jose[cryptography].
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    key_material = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(key_material)
    return Fernet(key)


def encrypt_text(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
