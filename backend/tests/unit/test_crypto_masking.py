"""Tests for crypto masking functionality - RED Phase tests.

TAG: [SPEC-004] [SECURITY] [CRYPTO] [MASKING-TEST]
REQ: REQ-008 - Auth Config Security

Additional tests to improve coverage for mask_auth_config function.
"""


from app.utils.crypto import mask_auth_config


class TestMaskAuthConfigEdgeCases:
    """Test edge cases for mask_auth_config function.

    These tests target lines 205, 209 in crypto.py which had missing coverage.
    """

    def test_mask_short_sensitive_value_returns_asterisks(self):
        """Test that short values (<=8 chars) are masked with ***.

        Targets line 205: masked[key] = "***"
        """
        config = {"api_key": "short"}

        result = mask_auth_config(config)

        assert result == {"api_key": "***"}
        assert config["api_key"] == "short"  # Original unchanged

    def test_mask_exactly_8_chars_returns_asterisks(self):
        """Test that exactly 8 char values are masked with ***."""
        config = {"api_key": "12345678"}

        result = mask_auth_config(config)

        assert result == {"api_key": "***"}

    def test_mask_9_chars_show_first_and_last(self):
        """Test that 9+ char values show first/4 and last/4."""
        config = {"api_key": "123456789"}

        result = mask_auth_config(config)

        assert result == {"api_key": "1234***6789"}

    def test_mask_numeric_value(self):
        """Test that numeric sensitive values are masked.

        Targets line 209: masked[key] = "***" (non-string values)
        """
        config = {"token": 12345}

        result = mask_auth_config(config)

        assert result == {"token": "***"}
        assert config["token"] == 12345  # Original unchanged

    def test_mask_boolean_value(self):
        """Test that boolean sensitive values are masked."""
        config = {"secret": True}

        result = mask_auth_config(config)

        assert result == {"secret": "***"}

    def test_mask_list_value(self):
        """Test that list sensitive values are masked."""
        config = {"password": ["pass1", "pass2"]}

        result = mask_auth_config(config)

        assert result == {"password": "***"}

    def test_mask_none_value_remains_none(self):
        """Test that None values remain None (not masked)."""
        config = {"api_key": None}

        result = mask_auth_config(config)

        assert result == {"api_key": None}

    def test_mask_multiple_sensitive_fields(self):
        """Test masking multiple sensitive fields in one config."""
        config = {
            "api_key": "short",
            "token": 12345,
            "password": None,
            "non_sensitive": "visible",
        }

        result = mask_auth_config(config)

        assert result == {
            "api_key": "***",
            "token": "***",
            "password": None,
            "non_sensitive": "visible",
        }

    def test_mask_nested_dict_with_sensitive_values(self):
        """Test masking nested dictionaries with various value types."""
        config = {
            "credentials": {
                "username": "user",
                "api_key": "short",
                "timeout": 30,  # Non-sensitive
            }
        }

        result = mask_auth_config(config)

        assert result == {
            "credentials": {
                "username": "user",
                "api_key": "***",
                "timeout": 30,
            }
        }

    def test_mask_auth_config_none_returns_none(self):
        """Test that None input returns None."""
        result = mask_auth_config(None)
        assert result is None

    def test_mask_client_secret(self):
        """Test that client_secret field is properly masked.

        This tests the duplicate 'client_secret' field in _SENSITIVE_FIELDS.
        """
        config = {"client_secret": "mysecret"}

        result = mask_auth_config(config)

        assert result == {"client_secret": "***"}
