"""
Email utility functions for user notifications.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_verification_email(email: str, otp: str, tenant_name: str, tenant_id: str = 'none') -> bool:
    """
    Send email verification OTP to user with verification link.
    
    Args:
        email: User's email address
        otp: 6-digit verification OTP
        tenant_name: Name of the tenant
        tenant_id: Tenant UUID for link generation
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = f'Email Verification - {tenant_name}'
        
        # Generate verification link
        from urllib.parse import quote
        verification_link = f"{settings.FRONTEND_URL}/api/v1/verify-email/?tenant={tenant_id}&email={email}&tenant_name={quote(tenant_name)}"
        
        # HTML email
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #667eea;">Welcome to {tenant_name}!</h2>
                    <p>Thank you for registering. Please verify your email address to activate your account.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" 
                           style="display: inline-block; background: grey; 
                                  color: black; padding: 15px 40px; text-decoration: none; border-radius: 8px; 
                                  font-weight: bold; font-size: 16px;">
                            Verify Email
                        </a>
                    </div>
                    
                    <p>Or enter this verification code manually:</p>
                    <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
                        <h1 style="color: #4CAF50; font-size: 48px; letter-spacing: 10px; margin: 0;">
                            {otp}
                        </h1>
                    </div>
                    
                    <p><strong>This code is valid for 1 hour.</strong></p>
                    
                    <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                        If you didn't request this, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Plain text fallback
        plain_message = f"""
        Welcome to {tenant_name}!
        
        Thank you for registering. Please verify your email address by clicking the link below:
        
        {verification_link}
        
        Or use the following OTP code:
        
        OTP: {otp}
        
        This OTP is valid for 1 hour.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info("Verification email with link sent")
        return True
        
    except Exception as e:
        logger.error("Failed to send verification email", exc_info=True)
        return False


def send_password_reset_email(email: str, otp: str, tenant_name: str) -> bool:
    """
    Send password reset OTP to user.
    
    Args:
        email: User's email address
        otp: 6-digit reset OTP
        tenant_name: Name of the tenant
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = f'Password Reset OTP - {tenant_name}'
        
        # HTML email
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>You requested to reset your password for {tenant_name}.</p>
                <p>Use the following OTP to reset your password:</p>
                <div style="background-color: #f4f4f4; padding: 20px; text-align: center; margin: 30px 0;">
                    <h1 style="color: #2196F3; font-size: 48px; letter-spacing: 10px; margin: 0;">
                        {otp}
                    </h1>
                </div>
                <p><strong>This OTP is valid for 1 hour.</strong></p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    If you didn't request this, please ignore this email.
                </p>
            </body>
        </html>
        """
        
        # Plain text fallback
        plain_message = f"""
        Password Reset Request
        
        You requested to reset your password for {tenant_name}.
        
        Use the following OTP to reset your password:
        
        OTP: {otp}
        
        This OTP is valid for 1 hour. If you didn't request this, please ignore this email.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info("Password reset OTP sent")
        return True
        
    except Exception as e:
        logger.error("Failed to send password reset OTP", exc_info=True)
        return False


def send_welcome_email(email: str, username: str, tenant_name: str) -> bool:
    """
    Send welcome email after successful email verification.
    
    Args:
        email: User's email address
        username: User's username
        tenant_name: Name of the tenant
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = f'Welcome to {tenant_name}!'
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Welcome, {username}!</h2>
                <p>Your email has been verified successfully.</p>
                <p>You can now enjoy all the features of {tenant_name}:</p>
                <ul>
                    <li>Create and manage playlists</li>
                    <li>Request songs</li>
                    <li>Discover new music</li>
                </ul>
                <p>Get started now and enjoy the music!</p>
            </body>
        </html>
        """
        
        plain_message = f"""
        Welcome, {username}!
        
        Your email has been verified successfully.
        
        You can now enjoy all the features of {tenant_name}.
        
        Get started now and enjoy the music!
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,  # Don't break flow if welcome email fails
        )
        
        logger.info("Welcome email sent")
        return True
        
    except Exception as e:
        logger.error("Failed to send welcome email", exc_info=True)
        return False
