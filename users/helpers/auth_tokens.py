"""
JWT token utilities for authentication.
"""
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

def blacklist_refresh_token(refresh_token: str) -> bool:
    """
    Blacklist a refresh token to invalidate it.
    
    Args:
        refresh_token: The refresh token string to blacklist
        
    Returns:
        True if successfully blacklisted, False otherwise
    """
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return True
    except TokenError:
        return False



