"""Tests for Tool auth_config masking functionality.

TAG: [SPEC-004] [SECURITY] [TOOL] [TEST]
REQ: REQ-008 - Auth Config Security

Tests for masking sensitive fields in Tool auth_config.
"""

import pytest


class TestMaskAuthConfig:
    """Test auth_config masking functionality."""

    def test_mask_auth_config_with_api_key(self):
        """Test masking API key in auth_config."""
        from app.utils.crypto import mask_auth_config

        config = {
            "api_key": "test_key_fake_12345",
            "type": "bearer",
        }
        masked = mask_auth_config(config)

        assert "api_key" in masked, "Masked config should have api_key field"
        assert masked["api_key"] != "test_key_fake_12345", "API key should be masked"
        assert "***" in masked["api_key"], "Masked value should contain asterisks"
        assert (
            masked["type"] == "bearer"
        ), "Non-sensitive fields should remain unchanged"

    def test_mask_auth_config_with_password(self):
        """Test masking password in auth_config."""
        from app.utils.crypto import mask_auth_config

        config = {
            "username": "user@example.com",
            "password": "FakePassword123!",
        }
        masked = mask_auth_config(config)

        assert masked["username"] == "user@example.com", "Username should not be masked"
        assert masked["password"] != "FakePassword123!", "Password should be masked"
        assert "***" in masked["password"], "Masked password should contain asterisks"

    def test_mask_auth_config_with_token(self):
        """Test masking token in auth_config."""
        from app.utils.crypto import mask_auth_config

        config = {
            "access_token": "test_token_xyz_789",
            "token_type": "Bearer",
        }
        masked = mask_auth_config(config)

        assert masked["token_type"] == "Bearer", "token_type should not be masked"
        assert masked["access_token"] != "test_token_xyz_789", "Token should be masked"

    def test_mask_auth_config_with_nested_dict(self):
        """Test masking nested auth_config."""
        from app.utils.crypto import mask_auth_config

        config = {
            "credentials": {
                "api_key": "test_key_abc",
                "secret": "fake_secret_123",
            },
            "region": "us-east-1",
        }
        masked = mask_auth_config(config)

        assert masked["region"] == "us-east-1", "Region should not be masked"
        assert (
            masked["credentials"]["api_key"] != "test_key_abc"
        ), "Nested API key should be masked"
        assert (
            masked["credentials"]["secret"] != "fake_secret_123"
        ), "Nested secret should be masked"

    def test_mask_auth_config_with_empty_dict(self):
        """Test masking empty auth_config."""
        from app.utils.crypto import mask_auth_config

        config = {}
        masked = mask_auth_config(config)

        assert masked == {}, "Empty config should remain empty"

    def test_mask_auth_config_with_no_sensitive_fields(self):
        """Test masking config with no sensitive fields."""
        from app.utils.crypto import mask_auth_config

        config = {
            "type": "oauth",
            "scope": "read write",
            "region": "us-west-2",
        }
        masked = mask_auth_config(config)

        assert masked == config, "Non-sensitive config should remain unchanged"

    def test_mask_auth_config_with_none_value(self):
        """Test masking config with None values."""
        from app.utils.crypto import mask_auth_config

        config = {
            "api_key": None,
            "type": "bearer",
        }
        masked = mask_auth_config(config)

        assert masked["api_key"] is None, "None values should remain None"
        assert (
            masked["type"] == "bearer"
        ), "Non-sensitive fields should remain unchanged"

    def test_mask_auth_config_known_sensitive_fields(self):
        """Test that all known sensitive field names are masked."""
        from app.utils.crypto import mask_auth_config

        sensitive_fields = [
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
        ]

        for field in sensitive_fields:
            config = {field: "test_fake_value", "other": "keep_this"}
            masked = mask_auth_config(config)

            assert masked[field] != "test_fake_value", f"{field} should be masked"
            assert "***" in masked[field], f"Masked {field} should contain asterisks"
            assert masked["other"] == "keep_this", "Other fields should not be masked"


class TestToolModelAuthMasking:
    """Test Tool model integration with auth_config masking."""

    @pytest.mark.asyncio
    async def test_tool_get_masked_auth_config(self, db_session):
        """Test Tool.get_masked_auth_config method."""
        import uuid

        from app.models.enums import ToolType
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Test Tool",
            tool_type=ToolType.HTTP,
            auth_config={
                "api_key": "test_key_fake",
                "type": "bearer",
            },
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        masked = tool.get_masked_auth_config()

        assert masked is not None, "Masked config should not be None"
        assert masked["api_key"] != "test_key_fake", "API key should be masked"
        assert "***" in masked["api_key"], "Masked value should contain asterisks"

    @pytest.mark.asyncio
    async def test_tool_get_masked_auth_config_with_none(self, db_session):
        """Test Tool.get_masked_auth_config when auth_config is None."""
        import uuid

        from app.models.enums import ToolType
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Test Tool",
            tool_type=ToolType.HTTP,
            auth_config=None,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        masked = tool.get_masked_auth_config()

        assert masked is None, "None auth_config should return None"

    @pytest.mark.asyncio
    async def test_tool_repr_shows_masked_auth(self, db_session):
        """Test that Tool.__repr__ doesn't expose sensitive data."""
        import uuid

        from app.models.enums import ToolType
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Test Tool",
            tool_type=ToolType.HTTP,
            auth_config={
                "api_key": "test_key_fake",
            },
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        repr_str = repr(tool)

        # Should not contain actual secret
        assert (
            "test_key_fake" not in repr_str
        ), "repr should not expose auth_config secrets"
