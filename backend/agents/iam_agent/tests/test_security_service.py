from app.services.security import SecurityService


def test_validate_password_strength_accepts_strong_password():
    is_valid, error = SecurityService.validate_password_strength("SecurePass123!")

    assert is_valid is True
    assert error == ""


def test_validate_password_strength_rejects_short_password():
    is_valid, error = SecurityService.validate_password_strength("Short1!")

    assert is_valid is False
    assert "8 characters" in error


def test_validate_password_strength_rejects_missing_uppercase():
    is_valid, error = SecurityService.validate_password_strength("lowercase123!")

    assert is_valid is False
    assert "uppercase" in error


def test_validate_password_strength_rejects_missing_lowercase():
    is_valid, error = SecurityService.validate_password_strength("UPPERCASE123!")

    assert is_valid is False
    assert "lowercase" in error


def test_validate_password_strength_rejects_missing_digit():
    is_valid, error = SecurityService.validate_password_strength("NoDigits!")

    assert is_valid is False
    assert "number" in error or "digit" in error


def test_sanitize_input_preserves_safe_input():
    assert SecurityService.sanitize_input("test@example.com") == "test@example.com"


def test_is_safe_email_accepts_valid_email():
    assert SecurityService.is_safe_email("test@example.com") is True


def test_is_safe_email_rejects_invalid_email():
    assert SecurityService.is_safe_email("not-an-email") is False


def test_is_safe_email_rejects_script_injection_shape():
    assert SecurityService.is_safe_email("test<script>@example.com") is False
