"""
Celery task for cleaning up expired JWT tokens.
"""
from celery import shared_task
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
import logging

logger = logging.getLogger(__name__)


@shared_task(name='cleanup_expired_tokens')
def cleanup_expired_tokens():
    """
    Delete expired tokens from database.
    Runs daily to prevent token table bloat.
    Tokens older than 2 days are removed (matching REFRESH_TOKEN_LIFETIME).
    """
    now = timezone.now()
    
    # Delete blacklisted tokens older than 2 days
    blacklisted_cutoff = now - timezone.timedelta(days=2)
    blacklisted_count = BlacklistedToken.objects.filter(
        token__expires_at__lt=blacklisted_cutoff
    ).delete()[0]
    
    # Delete outstanding tokens that expired more than 2 days ago
    outstanding_cutoff = now - timezone.timedelta(days=2)
    outstanding_count = OutstandingToken.objects.filter(
        expires_at__lt=outstanding_cutoff
    ).delete()[0]
    
    logger.info(f"Token cleanup: Removed {blacklisted_count} blacklisted tokens")
    logger.info(f"Token cleanup: Removed {outstanding_count} outstanding tokens")
    
    return {
        'blacklisted_removed': blacklisted_count,
        'outstanding_removed': outstanding_count,
        'timestamp': now.isoformat()
    }
