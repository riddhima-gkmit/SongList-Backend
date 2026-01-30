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
ACCESS_TOKEN_BLACKLIST_TTL = 3600  # 1 hour (same as access token lifetime)
MAX_OTP_ATTEMPTS = 3
SUBSCRIPTION_CACHE_TTL = 300  # 5 minutes

# Payment
PREMIUM_AMOUNT = 999.00  # Lifetime subscription price in INR
PAYMENT_CURRENCY = "INR"

# Song validation
MIN_RELEASE_YEAR = 1800  # Minimum allowed release year for songs

# OTP Configuration
OTP_LENGTH = 6  # Length of OTP codes

# Token Management
ACCESS_TOKEN_DENYLIST_TTL = 720  # 12 minutes (denylist TTL for access tokens)

# Phone Number Validation
PHONE_NUMBER_DIGITS = 10  # Required number of digits in phone number

# Cache TTLs (seconds)
GENRES_LIST_CACHE_TTL = 3600  # 1 hour
SONGS_LIST_CACHE_TTL = 300  # 5 minutes
TENANT_SONGS_LIST_CACHE_TTL = 300  # 5 minutes