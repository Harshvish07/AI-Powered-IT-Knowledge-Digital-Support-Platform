import re

PASSWORD_MIN_LENGTH = 8


def validate_password_strength(password: str) -> str:
    """Raises ValueError with a human-readable message if the password is too weak."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[^\w\s]", password):
        raise ValueError("Password must contain at least one special character.")
    return password
