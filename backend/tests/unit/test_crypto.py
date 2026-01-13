"""Tests for crypto utility module.

TAG: [SPEC-004] [SECURITY] [CRYPTO] [TEST]
REQ: REQ-008 - Auth Config Security

Tests for encryption and decryption of sensitive data using Fernet.
"""

import pytest


class TestFernetKeyGeneration:
    """Test Fernet key generation functionality."""

    def test_generate_fernet_key_returns_bytes(self):
        """Test that generate_fernet_key returns bytes."""
        from app.utils.crypto import generate_fernet_key

        key = generate_fernet_key()
        assert isinstance(key, bytes), "Key should be bytes"
        assert len(key) == 44, "Fernet key should be 44 bytes (base64 encoded)"

    def test_generate_fernet_key_is_unique(self):
        """Test that generate_fernet_key produces unique keys."""
        from app.utils.crypto import generate_fernet_key

        key1 = generate_fernet_key()
        key2 = generate_fernet_key()
        assert key1 != key2, "Each generated key should be unique"


class TestFernetEncryption:
    """Test Fernet encryption functionality."""

    @pytest.fixture
    def fernet_key(self):
        """Provide a valid Fernet key for testing."""
        from cryptography.fernet import Fernet

        return Fernet.generate_key()

    def test_encrypt_dict_returns_encrypted_data(self, fernet_key):
        """Test that encrypt_dict returns encrypted bytes."""
        from app.utils.crypto import encrypt_dict

        data = {"api_key": "secret123", "token": "abc123"}
        encrypted = encrypt_dict(data, fernet_key)

        assert isinstance(encrypted, bytes), "Encrypted data should be bytes"
        assert encrypted != b'{"api_key": "secret123"}', "Data should be encrypted"

    def test_encrypt_dict_with_empty_dict(self, fernet_key):
        """Test that encrypt_dict handles empty dict."""
        from app.utils.crypto import encrypt_dict

        data = {}
        encrypted = encrypt_dict(data, fernet_key)

        assert isinstance(encrypted, bytes), "Encrypted empty dict should be bytes"

    def test_encrypt_dict_with_nested_dict(self, fernet_key):
        """Test that encrypt_dict handles nested dictionaries."""
        from app.utils.crypto import encrypt_dict

        data = {
            "credentials": {
                "username": "user",
                "password": "pass",
            },
            "settings": {"timeout": 30},
        }
        encrypted = encrypt_dict(data, fernet_key)

        assert isinstance(encrypted, bytes), "Encrypted nested dict should be bytes"

    def test_encrypt_dict_requires_key(self):
        """Test that encrypt_dict raises error without key."""
        from app.utils.crypto import encrypt_dict

        data = {"api_key": "secret"}

        with pytest.raises(TypeError):
            encrypt_dict(data, None)


class TestFernetDecryption:
    """Test Fernet decryption functionality."""

    @pytest.fixture
    def fernet_key(self):
        """Provide a valid Fernet key for testing."""
        from cryptography.fernet import Fernet

        return Fernet.generate_key()

    def test_decrypt_dict_returns_original_data(self, fernet_key):
        """Test that decrypt_dict returns original data."""
        from app.utils.crypto import decrypt_dict, encrypt_dict

        original = {"api_key": "secret123", "token": "abc123"}
        encrypted = encrypt_dict(original, fernet_key)
        decrypted = decrypt_dict(encrypted, fernet_key)

        assert decrypted == original, "Decrypted data should match original"

    def test_decrypt_dict_with_empty_dict(self, fernet_key):
        """Test that decrypt_dict handles empty dict."""
        from app.utils.crypto import decrypt_dict, encrypt_dict

        original = {}
        encrypted = encrypt_dict(original, fernet_key)
        decrypted = decrypt_dict(encrypted, fernet_key)

        assert decrypted == {}, "Decrypted empty dict should be empty"

    def test_decrypt_dict_with_nested_dict(self, fernet_key):
        """Test that decrypt_dict handles nested dictionaries."""
        from app.utils.crypto import decrypt_dict, encrypt_dict

        original = {
            "credentials": {"username": "user", "password": "pass"},
            "settings": {"timeout": 30},
        }
        encrypted = encrypt_dict(original, fernet_key)
        decrypted = decrypt_dict(encrypted, fernet_key)

        assert decrypted == original, "Decrypted nested dict should match original"

    def test_decrypt_dict_requires_correct_key(self, fernet_key):
        """Test that decrypt_dict fails with wrong key."""
        from cryptography.fernet import Fernet

        from app.utils.crypto import decrypt_dict, encrypt_dict

        original = {"api_key": "secret123"}
        encrypted = encrypt_dict(original, fernet_key)

        wrong_key = Fernet.generate_key()
        from cryptography.fernet import InvalidToken

        with pytest.raises(InvalidToken):
            decrypt_dict(encrypted, wrong_key)

    def test_decrypt_dict_requires_key(self):
        """Test that decrypt_dict raises error without key."""
        from app.utils.crypto import decrypt_dict

        with pytest.raises(TypeError):
            decrypt_dict(b"encrypted_data", None)


class TestGetFernetKey:
    """Test getting Fernet key from environment."""

    def test_get_fernet_key_from_env(self, monkeypatch):
        """Test getting Fernet key from environment variable."""
        from cryptography.fernet import Fernet

        from app.utils.crypto import get_fernet_key

        # Generate a valid key
        valid_key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", valid_key)

        key = get_fernet_key()
        assert key == valid_key.encode(), "Should return key from environment"

    def test_get_fernet_key_generates_if_missing(self, monkeypatch):
        """Test that get_fernet_key generates key if not in env."""
        from app.utils.crypto import get_fernet_key

        # Remove ENCRYPTION_KEY from environment
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        key = get_fernet_key()
        assert isinstance(key, bytes), "Should generate bytes key"
        assert len(key) == 44, "Generated key should be valid Fernet key"

    def test_get_fernet_key_raises_on_invalid_key(self, monkeypatch):
        """Test that get_fernet_key raises error on invalid key."""
        from app.utils.crypto import get_fernet_key

        invalid_key = "not_a_valid_fernet_key"
        monkeypatch.setenv("ENCRYPTION_KEY", invalid_key)

        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY"):
            get_fernet_key()
