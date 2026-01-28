"""
Global constants for the SongList application.
"""

# Pagination
PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# Cache TTLs (seconds)
EMAIL_VERIFY_TTL = 3600  # 1 hour
LOGIN_OTP_TTL = 300  # 5 minutes
PASSWORD_RESET_TTL = 3600  # 1 hour
MAX_OTP_ATTEMPTS = 3

# Payment
PREMIUM_AMOUNT = 999.00  # Lifetime subscription price in INR

# Song validation
MIN_RELEASE_YEAR = 1800  # Minimum allowed release year for songs

# OTP Configuration
OTP_LENGTH = 6  # Length of OTP codes

# Token Management
ACCESS_TOKEN_DENYLIST_TTL = 1800  # 30 minutes (denylist TTL for access tokens - matches access token lifetime)

# Phone Number Validation
PHONE_NUMBER_DIGITS = 10  # Required number of digits in phone number

