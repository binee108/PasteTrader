"""Encryption utility for sensitive data.

TAG: [SPEC-004] [SECURITY] [CRYPTO]
REQ: REQ-008 - Auth Config Security

This module provides encryption and decryption functions for sensitive data
using Fernet symmetric encryption (AES-128-CBC with HMAC).

Features:
- Fernet key generation
- Dictionary encryption/decryption
- Environment-based key management
- Base64 encoding for encrypted data
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

from cryptography.fernet import Fernet


def generate_fernet_key() -> bytes:
    """Generate a new Fernet encryption key.

    Returns:
        A URL-safe base64-encoded 32-byte key.
        The key is 44 bytes when encoded (including padding).

    Note:
        - Store this key securely (e.g., environment variable)
        - Do NOT commit keys to version control
        - Key rotation strategy should be planned for production
        - Lost keys cannot recover encrypted data

    Example:
        >>> key = generate_fernet_key()
        >>> len(key)
        44
        >>> isinstance(key, bytes)
        True
    """
    return Fernet.generate_key()


def encrypt_dict(data: dict[str, Any], key: bytes) -> bytes:
    """Encrypt a dictionary using Fernet symmetric encryption.

    Args:
        data: Dictionary to encrypt (will be JSON-serialized)
        key: Fernet encryption key (44 bytes)

    Returns:
        Encrypted data as bytes

    Raises:
        TypeError: If key is None or not bytes
        ValueError: If key is invalid Fernet key

    Example:
        >>> key = generate_fernet_key()
        >>> data = {"api_key": "secret123"}
        >>> encrypted = encrypt_dict(data, key)
        >>> isinstance(encrypted, bytes)
        True
    """
    if key is None:
        raise TypeError("Encryption key cannot be None")

    fernet = Fernet(key)
    json_data = json.dumps(data).encode("utf-8")
    return fernet.encrypt(json_data)


def decrypt_dict(encrypted_data: bytes, key: bytes) -> dict[str, Any]:
    """Decrypt Fernet-encrypted data back to a dictionary.

    Args:
        encrypted_data: Encrypted bytes from encrypt_dict
        key: Fernet encryption key (must match encryption key)

    Returns:
        Decrypted dictionary

    Raises:
        TypeError: If key is None or not bytes
        ValueError: If decrypted data is not a valid dictionary
        InvalidToken: If key is incorrect or data is corrupted

    Example:
        >>> key = generate_fernet_key()
        >>> original = {"api_key": "secret123"}
        >>> encrypted = encrypt_dict(original, key)
        >>> decrypted = decrypt_dict(encrypted, key)
        >>> decrypted == original
        True
    """
    if key is None:
        raise TypeError("Decryption key cannot be None")

    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data)
    result: Any = json.loads(decrypted_data.decode("utf-8"))

    # Type safety check: ensure result is a dictionary
    if not isinstance(result, dict):
        raise ValueError(
            f"Decrypted data is not a dictionary, got {type(result).__name__}"
        )

    return cast("dict[str, Any]", result)


def get_fernet_key() -> bytes:
    """Get Fernet key from environment or generate a new one.

    This function first tries to read ENCRYPTION_KEY from environment.
    If not found, it generates a new key.

    Returns:
        Fernet encryption key as bytes

    Raises:
        ValueError: If ENCRYPTION_KEY is set but invalid

    Note:
        In production, always set ENCRYPTION_KEY environment variable.
        Generated keys should be saved to environment for persistence.

    Example:
        >>> import os
        >>> os.environ["ENCRYPTION_KEY"] = generate_fernet_key().decode()
        >>> key = get_fernet_key()
        >>> isinstance(key, bytes)
        True
    """
    env_key = os.getenv("ENCRYPTION_KEY")

    if env_key:
        key = env_key.encode("utf-8")
        # Validate the key
        try:
            Fernet(key)
        except ValueError as e:
            raise ValueError(
                f"Invalid ENCRYPTION_KEY in environment: {e}. "
                "Generate a valid key using: cryptography.fernet.Fernet.generate_key()"
            )
        return key

    # Generate new key if not in environment
    return generate_fernet_key()


# Sensitive field names that should be masked in auth_config
_SENSITIVE_FIELDS = {
    "api_key",
    "apikey",
    "apiKey",
    "secret",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
    "auth_token",
    "client_secret",
}


def mask_auth_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    """Mask sensitive fields in auth_config dictionary.

    This function creates a copy of the config with sensitive field values
    replaced with asterisks for logging/display purposes.

    Args:
        config: Auth configuration dictionary or None

    Returns:
        New dictionary with sensitive values masked, or None if input is None

    Note:
        - Does NOT modify the original config
        - Only masks values, preserves field names
        - Recursively handles nested dictionaries
        - None values remain None (not masked)

    Example:
        >>> config = {"api_key": "secret123", "type": "bearer"}
        >>> masked = mask_auth_config(config)
        >>> masked["api_key"]
        '***'
        >>> masked["type"]
        'bearer'
        >>> config["api_key"]  # Original unchanged
        'secret123'
    """
    if config is None:
        return None

    masked: dict[str, Any] = {}
    for key, value in config.items():
        if key in _SENSITIVE_FIELDS:
            # Mask sensitive field
            if value is None:
                masked[key] = None
            elif isinstance(value, str):
                # Show first 4 and last 4 chars with *** in between
                if len(value) <= 8:
                    masked[key] = "***"
                else:
                    masked[key] = f"{value[:4]}***{value[-4:]}"
            else:
                masked[key] = "***"
        elif isinstance(value, dict):
            # Recursively mask nested dictionaries
            masked[key] = mask_auth_config(value)
        else:
            # Keep non-sensitive fields as-is
            masked[key] = value

    return masked


__all__ = [
    "decrypt_dict",
    "encrypt_dict",
    "generate_fernet_key",
    "get_fernet_key",
    "mask_auth_config",
]
