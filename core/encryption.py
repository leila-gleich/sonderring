import base64
import hashlib
import hmac
import os
import sys
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

INSECURE_DEFAULT_KEY = 'c29uZGVycmluZy1hZXMtMjU2LXNlY3JldC1rZXktMzI='


class ConfirmationEncryptor:
    """
    AES-256-GCM Application-Level Field Encryptor with:
    - Key Versioning (v1:<base64>) for zero-downtime key rotation
    - Authenticated Encryption with Associated Data (AAD) context binding
    - Production key enforcement (blocks insecure defaults when DEBUG=False)
    - HMAC-SHA256 blind indexing support
    """
    CURRENT_VERSION = 'v1'

    @classmethod
    def _normalize_key(cls, raw_key) -> bytes:
        if isinstance(raw_key, bytes):
            key_bytes = raw_key
        elif isinstance(raw_key, str):
            try:
                key_bytes = base64.b64decode(raw_key.encode('utf-8'))
            except Exception:
                key_bytes = raw_key.encode('utf-8')
        else:
            raise ImproperlyConfigured("Invalid FIELD_ENCRYPTION_KEY format.")

        if len(key_bytes) not in (16, 24, 32):
            # Derive a 32-byte key deterministically via SHA-256 if non-standard length
            key_bytes = hashlib.sha256(key_bytes).digest()
        return key_bytes

    @classmethod
    def _get_keyring(cls) -> dict[str, bytes]:
        debug = getattr(settings, 'DEBUG', False)
        configured_keyring = getattr(settings, 'FIELD_ENCRYPTION_KEYS', None)
        if configured_keyring and isinstance(configured_keyring, dict):
            return {ver: cls._normalize_key(k) for ver, k in configured_keyring.items()}

        raw_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not raw_key:
            raise ImproperlyConfigured(
                "FIELD_ENCRYPTION_KEY must be configured in settings or environment."
            )
        enforce_prod = getattr(
            settings,
            'ENFORCE_PRODUCTION_KEYS',
            (not debug and 'test' not in sys.argv)
        )
        if enforce_prod and raw_key == INSECURE_DEFAULT_KEY:
            raise ImproperlyConfigured(
                "Refusing to use default development FIELD_ENCRYPTION_KEY when DEBUG=False."
            )
        return {cls.CURRENT_VERSION: cls._normalize_key(raw_key)}

    @classmethod
    def _get_key(cls, version: str = CURRENT_VERSION) -> bytes:
        keyring = cls._get_keyring()
        if version in keyring:
            return keyring[version]
        # Fallback to primary key
        return next(iter(keyring.values()))

    @staticmethod
    def _encode_aad(aad: str | bytes | None) -> bytes | None:
        if aad is None:
            return None
        if isinstance(aad, bytes):
            return aad
        return str(aad).encode('utf-8')

    @classmethod
    def is_encrypted(cls, value: str) -> bool:
        if not value or not isinstance(value, str):
            return False
        return value.startswith(f"{cls.CURRENT_VERSION}:")

    @classmethod
    def encrypt(cls, plaintext: str, aad: str | bytes | None = None) -> str:
        if not plaintext:
            return plaintext
        if cls.is_encrypted(plaintext):
            return plaintext
        key = cls._get_key(cls.CURRENT_VERSION)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        aad_bytes = cls._encode_aad(aad)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), aad_bytes)
        payload = base64.b64encode(nonce + ciphertext).decode('utf-8')
        return f"{cls.CURRENT_VERSION}:{payload}"

    @classmethod
    def decrypt(cls, encrypted_text: str, aad: str | bytes | None = None, strict: bool = False) -> str:
        if not encrypted_text:
            return encrypted_text

        aad_bytes = cls._encode_aad(aad)

        # Versioned AEAD token (e.g. "v1:<base64>")
        if ':' in encrypted_text and encrypted_text.split(':', 1)[0].startswith('v'):
            version, b64_payload = encrypted_text.split(':', 1)
            key = cls._get_key(version)
            decoded = base64.b64decode(b64_payload.encode('utf-8'))
            nonce, ciphertext = decoded[:12], decoded[12:]
            aesgcm = AESGCM(key)
            try:
                return aesgcm.decrypt(nonce, ciphertext, aad_bytes).decode('utf-8')
            except InvalidTag as exc:
                raise ValueError(
                    "AES-GCM authentication tag verification failed: ciphertext tampered or AAD context mismatch."
                ) from exc

        # Legacy unversioned base64 ciphertext support
        try:
            decoded = base64.b64decode(encrypted_text.encode('utf-8'), validate=True)
            if len(decoded) >= 28:  # 12-byte nonce + at least 16-byte GCM tag
                nonce, ciphertext = decoded[:12], decoded[12:]
                aesgcm = AESGCM(cls._get_key(cls.CURRENT_VERSION))
                try:
                    return aesgcm.decrypt(nonce, ciphertext, aad_bytes).decode('utf-8')
                except InvalidTag:
                    if aad_bytes is not None and not strict:
                        # Legacy token encrypted prior to AAD binding
                        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
                    raise
        except Exception:
            if strict:
                raise
            # Graceful fallback for legacy plaintext rows prior to migration
            return encrypted_text

        return encrypted_text

    @classmethod
    def blind_index(cls, value: str) -> str:
        """Computes a deterministic HMAC-SHA256 blind index for exact-match lookups on encrypted PII."""
        if not value:
            return ""
        secret = getattr(settings, 'SECRET_KEY', '').encode('utf-8')
        normalized = value.strip().lower().encode('utf-8')
        return hmac.new(secret, normalized, hashlib.sha256).hexdigest()


class EncryptedMixin:
    """Django model field mixin that transparently encrypts/decrypts values via AES-256-GCM."""

    def __init__(self, *args, aad_context: str | None = None, **kwargs):
        self.aad_context = aad_context
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.aad_context is not None:
            kwargs['aad_context'] = self.aad_context
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        if ConfirmationEncryptor.is_encrypted(value):
            return value
        return ConfirmationEncryptor.encrypt(str(value), aad=self.aad_context)

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        return ConfirmationEncryptor.decrypt(value, aad=self.aad_context)

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return value
        if ConfirmationEncryptor.is_encrypted(value):
            return ConfirmationEncryptor.decrypt(value, aad=self.aad_context)
        return value


class EncryptedTextField(EncryptedMixin, models.TextField):
    """AES-256-GCM encrypted TextField."""


class EncryptedCharField(EncryptedMixin, models.CharField):
    """AES-256-GCM encrypted CharField."""
