"""Encryption service for secrets and environment variables.

Uses Fernet (symmetric encryption based on AES-128 in CBC mode) to encrypt/decrypt sensitive data.
Supports multiple encryption keys for different environments (prod, local, etc.).
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    """Service for encrypting and decrypting secrets using Fernet (AES-128)."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption service.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from ENCRYPTION_KEY env var.
        """
        # Get encryption key
        if encryption_key:
            self.key = encryption_key
        else:
            self.key = os.getenv("ENCRYPTION_KEY")

        if not self.key:
            raise ValueError(
                "No encryption key found. Set ENCRYPTION_KEY in environment variables."
            )

        # Initialize Fernet cipher
        try:
            self.cipher = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If ciphertext is invalid or was encrypted with a different key
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            raise InvalidToken("Decryption failed: invalid token or wrong encryption key")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded Fernet key (44 characters)
        """
        return Fernet.generate_key().decode('utf-8')


def get_encryption_service(encryption_key: Optional[str] = None) -> EncryptionService:
    """Get encryption service instance.

    Args:
        encryption_key: Optional encryption key. If None, reads from ENCRYPTION_KEY env var.

    Returns:
        EncryptionService instance
    """
    return EncryptionService(encryption_key=encryption_key)
