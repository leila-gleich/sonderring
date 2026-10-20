import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

class ConfirmationEncryptor:
    _transient_key = None

    @classmethod
    def _get_key(cls):
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            if cls._transient_key is None:
                cls._transient_key = AESGCM.generate_key(bit_length=256)
            return cls._transient_key
        if isinstance(key, str):
            return base64.b64decode(key.encode('utf-8'))
        return key

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return plaintext
        aesgcm = AESGCM(cls._get_key())
        nonce = AESGCM.generate_key(bit_length=96)[:12]
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        if not encrypted_text:
            return encrypted_text
        decoded = base64.b64decode(encrypted_text.encode('utf-8'))
        nonce = decoded[:12]
        ciphertext = decoded[12:]
        aesgcm = AESGCM(cls._get_key())
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
