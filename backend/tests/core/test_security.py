"""Password hashing and verification tests.

TAG: [SPEC-002] [AUTH] [SECURITY] [TEST]
REQ: REQ-002 - Password Hashing
REQ: REQ-006 - Password Verification

Tests for password hashing using bcrypt with cost factor 12,
following AC-004 to AC-007 acceptance criteria.
"""

import time

import pytest

from app.core.security import (
    PasswordComplexityError,
    hash_password,
    is_password_complex_enough,
    verify_password,
)


class TestHashPassword:
    """Test password hashing functionality (AC-004)."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Test that hash_password returns a bcrypt hash string."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        # Should return a string
        assert isinstance(hashed, str)

        # Should be bcrypt hash format (starts with $2b$12$)
        assert hashed.startswith("$2b$12$")

        # Should be 60 characters long (standard bcrypt length)
        assert len(hashed) == 60

    def test_hash_password_different_for_same_password(self):
        """Test that same password produces different hashes (AC-007)."""
        password = "SecurePass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # Both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_hash_password_empty_string(self):
        """Test hashing an empty password."""
        hashed = hash_password("")

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$12$")

    def test_hash_password_with_unicode(self):
        """Test hashing password with unicode characters."""
        password = "SecurePass123!🔐"
        hashed = hash_password(password)

        assert hashed.startswith("$2b$12$")
        assert verify_password(password, hashed)


class TestVerifyPassword:
    """Test password verification functionality (AC-005, AC-006)."""

    def test_verify_correct_password(self):
        """Test verifying the correct password (AC-005)."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        # Verification should return True
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test rejecting an incorrect password (AC-006)."""
        password = "SecurePass123!"
        wrong_password = "WrongPass456!"
        hashed = hash_password(password)

        # Verification should return False
        assert verify_password(wrong_password, hashed) is False

    def test_verify_timing_safe(self):
        """Test that verification uses timing-safe comparison (AC-030)."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        # Time multiple verifications
        times_correct = []
        times_incorrect = []

        for _ in range(10):
            start = time.perf_counter()
            verify_password(password, hashed)
            times_correct.append(time.perf_counter() - start)

        for _ in range(10):
            start = time.perf_counter()
            verify_password("wrongpassword", hashed)
            times_incorrect.append(time.perf_counter() - start)

        # Average times should be similar (within 50ms variance)
        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)

        assert abs(avg_correct - avg_incorrect) < 0.05  # 50ms tolerance

    def test_verify_performance_under_500ms(self):
        """Test that verification completes within 500ms (AC-031)."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        start = time.perf_counter()
        verify_password(password, hashed)
        elapsed = time.perf_counter() - start

        # Should complete within 500ms
        assert elapsed < 0.5

    def test_hash_performance_under_500ms(self):
        """Test that hashing completes within 500ms (AC-031)."""
        password = "SecurePass123!"

        start = time.perf_counter()
        hash_password(password)
        elapsed = time.perf_counter() - start

        # Should complete within 500ms
        assert elapsed < 0.5


class TestPasswordComplexity:
    """Test password complexity validation (REQ-004)."""

    def test_complex_password_passes(self):
        """Test that a complex password passes validation."""
        password = "SecurePass123!"
        assert is_password_complex_enough(password) is True

    def test_short_password_fails(self):
        """Test that password shorter than 8 characters fails."""
        password = "Short1!"
        assert is_password_complex_enough(password) is False

    def test_exactly_8_characters_passes(self):
        """Test that exactly 8 characters passes."""
        password = "Valid123!"
        assert is_password_complex_enough(password) is True

    def test_password_without_lowercase_fails(self):
        """Test that password without lowercase fails."""
        password = "INVALID123!"
        assert is_password_complex_enough(password) is False

    def test_password_without_uppercase_fails(self):
        """Test that password without uppercase fails."""
        password = "invalid123!"
        assert is_password_complex_enough(password) is False

    def test_password_without_number_fails(self):
        """Test that password without number fails."""
        password = "InvalidPass!"
        assert is_password_complex_enough(password) is False

    def test_password_with_only_lowercase_fails(self):
        """Test that password with only lowercase fails."""
        password = "aaaaaaaa"
        assert is_password_complex_enough(password) is False

    def test_error_message_for_complexity(self):
        """Test that complexity error has helpful message."""
        password = "short"
        with pytest.raises(PasswordComplexityError) as exc_info:
            is_password_complex_enough(password, raise_error=True)

        assert "password" in str(exc_info.value).lower()
        assert "character" in str(exc_info.value).lower()


class TestSecurityEdgeCases:
    """Test security-related edge cases."""

    def test_verify_with_invalid_hash_format(self):
        """Test verification with invalid hash format."""
        password = "SecurePass123!"
        invalid_hash = "not_a_valid_hash"

        # Should return False, not raise exception
        assert verify_password(password, invalid_hash) is False

    def test_verify_with_empty_hash(self):
        """Test verification with empty hash."""
        password = "SecurePass123!"
        empty_hash = ""

        # Should return False, not raise exception
        assert verify_password(password, empty_hash) is False

    def test_hash_with_whitespace_password(self):
        """Test hashing password with leading/trailing whitespace."""
        password = "  SecurePass123!  "
        hashed = hash_password(password)

        assert hashed.startswith("$2b$12$")
        assert verify_password(password, hashed)

    def test_verify_is_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "SecurePass123!"
        hashed = hash_password(password)

        # Different case should not match
        assert verify_password("securepass123!", hashed) is False
        assert verify_password("SECUREPASS123!", hashed) is False
