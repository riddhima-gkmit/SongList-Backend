"""
Celery task for cleaning up expired JWT tokens.
"""
import logging

from celery import shared_task
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from common.context import get_correlation_id

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
    
    logger.info(
        f"Token cleanup: Removed {blacklisted_count} blacklisted tokens",
        extra={"correlation_id": get_correlation_id()},
    )
    logger.info(
        f"Token cleanup: Removed {outstanding_count} outstanding tokens",
        extra={"correlation_id": get_correlation_id()},
    )
    
    return {
        'blacklisted_removed': blacklisted_count,
        'outstanding_removed': outstanding_count,
        'timestamp': now.isoformat()
    }
