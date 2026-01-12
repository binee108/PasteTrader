"""Email validation and normalization tests.

TAG: [SPEC-002] [AUTH] [EMAIL] [TEST]
REQ: REQ-007 - Email Normalization

Tests for email validation and normalization,
following AC-008 to AC-011 acceptance criteria.
"""


from app.utils.email import (
    is_valid_email_format,
    normalize_email,
)


class TestNormalizeEmail:
    """Test email normalization functionality (AC-008, AC-009)."""

    def test_convert_to_lowercase(self):
        """Test that email is converted to lowercase (AC-008)."""
        email = "Test@Example.COM"
        normalized = normalize_email(email)

        assert normalized == "test@example.com"
        assert normalized.islower()

    def test_trim_whitespace(self):
        """Test that whitespace is removed (AC-009)."""
        email = "  test@example.com  "
        normalized = normalize_email(email)

        assert normalized == "test@example.com"
        assert not normalized.startswith(" ")
        assert not normalized.endswith(" ")

    def test_lowercase_and_whitespace_combined(self):
        """Test both lowercase conversion and whitespace trimming."""
        email = "  Test@Example.COM  "
        normalized = normalize_email(email)

        assert normalized == "test@example.com"

    def test_empty_email(self):
        """Test normalizing an empty email."""
        assert normalize_email("") == ""
        assert normalize_email("   ") == ""

    def test_already_normalized_email(self):
        """Test email that is already normalized."""
        email = "test@example.com"
        assert normalize_email(email) == email

    def test_email_with_plus_tag(self):
        """Test that plus tags are preserved."""
        email = "user+tag@example.com"
        normalized = normalize_email(email)

        assert normalized == "user+tag@example.com"

    def test_email_with_dots(self):
        """Test that dots in local part are preserved."""
        email = "first.last@example.com"
        normalized = normalize_email(email)

        assert normalized == "first.last@example.com"


class TestValidateEmailFormat:
    """Test email format validation (AC-010, AC-011)."""

    def test_valid_simple_email(self):
        """Test accepting valid simple email (AC-011)."""
        assert is_valid_email_format("user@example.com") is True

    def test_valid_email_with_dots(self):
        """Test accepting valid email with dots."""
        assert is_valid_email_format("first.last@example.co.uk") is True

    def test_valid_email_with_plus_tag(self):
        """Test accepting valid email with plus tag."""
        assert is_valid_email_format("user+tag@example.com") is True

    def test_valid_email_with_numbers(self):
        """Test accepting valid email with numbers."""
        assert is_valid_email_format("user123@example.com") is True

    def test_valid_email_with_underscore(self):
        """Test accepting valid email with underscore."""
        assert is_valid_email_format("user_name@example.com") is True

    def test_valid_email_with_hyphen(self):
        """Test accepting valid email with hyphen."""
        assert is_valid_email_format("user-name@example.com") is True

    def test_invalid_email_missing_at(self):
        """Test rejecting email without @ symbol (AC-010)."""
        assert is_valid_email_format("invalid-email") is False

    def test_invalid_email_missing_domain(self):
        """Test rejecting email without domain."""
        assert is_valid_email_format("user@") is False

    def test_invalid_email_missing_local(self):
        """Test rejecting email without local part."""
        assert is_valid_email_format("@example.com") is False

    def test_invalid_email_multiple_at(self):
        """Test rejecting email with multiple @ symbols."""
        assert is_valid_email_format("user@example@com") is False

    def test_invalid_email_with_spaces(self):
        """Test rejecting email with spaces."""
        assert is_valid_email_format("user @example.com") is False

    def test_empty_email(self):
        """Test rejecting empty email."""
        assert is_valid_email_format("") is False

    def test_none_email(self):
        """Test rejecting None email."""
        assert is_valid_email_format(None) is False


class TestEmailEdgeCases:
    """Test email-related edge cases."""

    def test_normalize_then_validate(self):
        """Test that normalization produces valid emails."""
        email = "  Test@Example.COM  "
        normalized = normalize_email(email)

        assert is_valid_email_format(normalized) is True

    def test_subdomain_in_domain(self):
        """Test email with subdomain."""
        email = "user@mail.example.com"
        normalized = normalize_email(email)

        assert is_valid_email_format(normalized) is True

    def test_international_tld(self):
        """Test email with international TLD."""
        email = "user@example.co.kr"
        normalized = normalize_email(email)

        assert is_valid_email_format(normalized) is True

    def test_case_insensitive_domain(self):
        """Test that domain part is case-insensitive."""
        email1 = normalize_email("user@EXAMPLE.COM")
        email2 = normalize_email("user@example.com")

        assert email1 == email2
