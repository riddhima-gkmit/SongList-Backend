"""
Celery tasks for asynchronous email delivery.
All email tasks are idempotent, tenant-aware, and include retry logic.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

from common.context import get_correlation_id
from tenants.models import Tenant
from users.helpers import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from users.models import User

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_verification_otp_task(self, user_id: str, otp: str, tenant_id: str):
    """
    Send email verification OTP asynchronously.
    Idempotent and tenant-aware.
    
    Args:
        user_id: User UUID
        otp: 6-digit verification OTP
        tenant_id: Tenant UUID
    """
    try:
        user = User.objects.select_related('tenant').get(id=user_id)
        tenant_name = user.tenant.name if user.tenant else "SongList"
        
        # Send OTP email
        success = send_verification_email(user.email, otp, tenant_name, tenant_id)
        
        if not success:
            raise Exception("Email sending failed")
        
        logger.info(
            "Verification OTP sent",
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )
        return {'status': 'sent', 'user_id': user_id, 'email': user.email}
        
    except ObjectDoesNotExist:
        logger.error(
            f"User {user_id} not found, skipping OTP email",
            extra={"correlation_id": get_correlation_id(), "user_id": user_id},
        )
        return {"status": "user_not_found"}
    except Exception as exc:
        logger.error(
            "Failed to send verification OTP",
            exc_info=True,
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )
        raise


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_password_reset_otp_task(self, email: str, otp: str, tenant_id: str):
    """
    Send password reset OTP asynchronously.
    Idempotent and tenant-aware.
    
    Args:
        email: User's email address
        otp: 6-digit reset OTP
        tenant_id: Tenant UUID (or 'none')
    """
    try:
        # Get tenant name
        if tenant_id and tenant_id != 'none':
            tenant = Tenant.objects.get(id=tenant_id)
            tenant_name = tenant.name
        else:
            tenant_name = "SongList"
        
        # Send OTP email
        success = send_password_reset_email(email, otp, tenant_name)
        
        if not success:
            raise Exception("Email sending failed")
        
        logger.info(
            "Password reset OTP sent",
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
            },
        )
        return {'status': 'sent', 'email': email}
        
    except ObjectDoesNotExist:
        logger.error(
            f"Tenant {tenant_id} not found",
            extra={"correlation_id": get_correlation_id(), "tenant_id": tenant_id},
        )
        # Still try to send with default tenant name
        send_password_reset_email(email, otp, "SongList")
        return {'status': 'sent_default'}
    except Exception as exc:
        logger.error(
            "Failed to send password reset OTP",
            exc_info=True,
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
            },
        )
        raise


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_login_otp_task(self, email: str, otp: str, tenant_id: str):
    """
    Send login OTP asynchronously.
    Idempotent and tenant-aware.
    
    Args:
        email: User's email address
        otp: 6-digit login OTP
        tenant_id: Tenant UUID
    """
    try:
        # Get tenant name
        if tenant_id and tenant_id != 'none':
            tenant = Tenant.objects.get(id=tenant_id)
            tenant_name = tenant.name
        else:
            # For super admin (None) or no tenant
            tenant_name = "SongList"
        
        subject = f'Login OTP - {tenant_name}'
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Login Request</h2>
                <p>Use the following OTP to complete your login:</p>
                <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 30px 0;">
                    <h1 style="color: #FF9800; font-size: 48px; letter-spacing: 10px; margin: 0;">
                        {otp}
                    </h1>
                </div>
                <p><strong>This OTP is valid for 5 minutes.</strong></p>
                <p style="color: #999; font-size: 12px;">
                    If you didn't request this, please ignore this email.
                </p>
            </body>
        </html>
        """
        
        plain_message = f"""
        Login Request
        
        Use the following OTP to complete your login:
        
        OTP: {otp}
        
        This OTP is valid for 5 minutes.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(
            "Login OTP sent",
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
            },
        )
        return {'status': 'sent', 'email': email}
        
    except Exception as exc:
        logger.error(
            "Failed to send login OTP",
            exc_info=True,
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": tenant_id,
            },
        )
        raise


@shared_task(
    bind=True,
    max_retries=2,  # Welcome email is less critical
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_welcome_email_task(self, user_id: str):
    """
    Send welcome email after successful verification.
    Idempotent and tenant-aware.
    
    Args:
        user_id: User UUID
    """
    try:
        user = User.objects.select_related('tenant').get(id=user_id)
        tenant_name = user.tenant.name if user.tenant else "SongList"
        
        success = send_welcome_email(user.email, user.username, tenant_name)
        
        if not success:
            logger.warning(
                "Welcome email failed",
                extra={"correlation_id": get_correlation_id(), "user_id": user_id},
            )
            return {'status': 'failed_non_critical'}
        
        logger.info(
            "Welcome email sent",
            extra={
                "correlation_id": get_correlation_id(),
                "tenant_id": str(user.tenant.id) if user.tenant else None,
                "user_id": user_id,
            },
        )
        return {'status': 'sent', 'user_id': user_id}
        
    except ObjectDoesNotExist:
        logger.error(
            f"User {user_id} not found, skipping welcome email",
            extra={"correlation_id": get_correlation_id(), "user_id": user_id},
        )
        return {"status": "user_not_found"}
    except Exception as exc:
        logger.error(
            "Failed to send welcome email",
            exc_info=True,
            extra={"correlation_id": get_correlation_id(), "user_id": user_id},
        )
        # Don't raise - welcome email is not critical
        return {'status': 'failed'}
