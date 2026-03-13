"""
Cache key generators for user-related operations.
All keys are tenant-prefixed for multi-tenant isolation.
"""


def get_verify_email_key(tenant_id: str, email: str) -> str:
    """Generate cache key for email verification token."""
    return f"tenant:{tenant_id}:verify:email:{email}"


def get_reset_password_key(tenant_id: str, email: str) -> str:
    """Generate cache key for password reset token."""
    return f"tenant:{tenant_id}:reset:password:{email}"


def get_login_otp_key(tenant_id: str, email: str) -> str:
    """Generate cache key for login OTP."""
    return f"tenant:{tenant_id}:login:otp:{email}"




