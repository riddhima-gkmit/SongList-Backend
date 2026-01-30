"""
Resend verification email view.
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status as http_status
from django.core.cache import cache

from common.responses import success_response, error_response
from users.models import User
from tenants.models import Tenant
from users.helpers import hash_token, get_verify_email_key
from users.helpers.otp_token import generate_otp
from common.constants import EMAIL_VERIFY_TTL, OTP_LENGTH


class ResendVerificationEmailAPIView(APIView):
    """Resend verification email with new OTP."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        email = request.data.get('email')
        
        if not email:
            return error_response("Email is required.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        if not tenant_id:
            return error_response("Tenant ID is required.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        try:
            tenant = Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            return error_response("Invalid or inactive tenant.", status_code=http_status.HTTP_404_NOT_FOUND)
        
        # Find user by email and tenant
        try:
            user = User.objects.get(email=email, tenant=tenant, is_verified=False)
        except User.DoesNotExist:
            # Return success even if user doesn't exist to prevent email enumeration
            return success_response(
                message="If the email exists and is not verified, a new verification code has been sent."
            )
        
        # Generate and cache new OTP
        otp = generate_otp(length=OTP_LENGTH)
        tenant_str = str(tenant_id)
        cache_key = get_verify_email_key(tenant_str, email)
        cache.set(cache_key, hash_token(otp), timeout=EMAIL_VERIFY_TTL)
        cache.set(f"{cache_key}:attempts", 0, timeout=EMAIL_VERIFY_TTL)
        
        # Send verification OTP asynchronously
        from users.tasks import send_verification_otp_task
        send_verification_otp_task.delay(str(user.id), otp, tenant_str)
        
        return success_response(
            message="A new verification code has been sent to your email.",
            data={"expires_in": EMAIL_VERIFY_TTL}
        )
