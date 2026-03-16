"""
OTP and token generation utilities for authentication flows.
"""
import secrets
import hashlib


def generate_verification_token(length: int = 64) -> str:
    """Generate a secure random token for email verification."""
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of specified length."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a plain token against its hashed version."""
    return hash_token(plain_token) == hashed_token



