"""Authentication views."""
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status as http_status

from common.responses import success_response, error_response
from common.constants import (
    EMAIL_VERIFY_TTL,
    PASSWORD_RESET_TTL,
    OTP_LENGTH,
    ACCESS_TOKEN_DENYLIST_TTL,
    LOGIN_OTP_TTL,
)
from users.serializers.auth_serializers import (
    RegisterSerializer,
    VerifyEmailSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    LogoutSerializer,
    VerifyLoginOTPSerializer,
    SuperAdminLoginSerializer,
    SuperAdminVerifyLoginOTPSerializer,
)
from users.helpers import (
    hash_token,
    blacklist_refresh_token,
    get_verify_email_key,
    get_reset_password_key,
    get_login_otp_key,
    generate_otp,
)
from users.tasks import (
    send_verification_otp_task,
    send_welcome_email_task,
    send_login_otp_task,
    send_password_reset_otp_task,
)
from tenants.models import Tenant
from users.helpers.otp_token import generate_otp, hash_token
from users.helpers.cache_keys import get_verify_email_key
from common.constants import EMAIL_VERIFY_TTL
from django.core.cache import cache
from users.services.registration import register_or_rewrite_user


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_id):
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=http_status.HTTP_404_NOT_FOUND)

        serializer = RegisterSerializer(
            data=request.data,
            context={"tenant": tenant}
        )
        serializer.is_valid(raise_exception=True)

        try:
            user, action = register_or_rewrite_user(
                tenant=tenant,
                data=serializer.validated_data
            )
        except ValueError as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return error_response(str(e), status_code=http_status.HTTP_403_FORBIDDEN)

        otp = generate_otp(length=OTP_LENGTH)
        key = get_verify_email_key(str(tenant.id), user.email)

        cache.set(key, hash_token(otp), EMAIL_VERIFY_TTL)
        cache.set(f"{key}:attempts", 0, EMAIL_VERIFY_TTL)

        send_verification_otp_task.delay(str(user.id), otp, str(tenant.id))


        return success_response(
            message="Check your email to verify your account.",
            data={"email": user.email},
            status_code=http_status.HTTP_201_CREATED
        )



class VerifyEmailAPIView(APIView):
    """Verify user email with token."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        serializer = VerifyEmailSerializer(
            data=request.data,
            context={'tenant_id': str(tenant_id) if tenant_id else 'none'}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.is_verified = True
        user.is_active = True
        user.save(update_fields=['is_verified', 'is_active'])
        
        # Clear cache
        cache_key = get_verify_email_key(str(tenant_id) if tenant_id else 'none', user.email)
        cache.delete(cache_key)
        cache.delete(f"{cache_key}:attempts")  # Clean up attempt counter
        
        send_welcome_email_task.delay(str(user.id))
        
        return success_response(message="Email verified successfully. You can now login.")


class LoginAPIView(APIView):
    """Request login OTP after password validation (2FA Step 1) - Tenant Scoped."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        serializer = LoginSerializer(
            data=request.data,
            context={'tenant_id': str(tenant_id) if tenant_id else None}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate and cache login OTP
        otp = generate_otp(length=6)
        cache_key = get_login_otp_key(str(tenant_id) if tenant_id else 'none', user.email)
        cache.set(cache_key, hash_token(otp), timeout=LOGIN_OTP_TTL)
        cache.set(f"{cache_key}:attempts", 0, timeout=LOGIN_OTP_TTL)
        
        send_login_otp_task.delay(user.email, otp, str(tenant_id) if tenant_id else 'none')
        
        return success_response(
            message="Login OTP has been sent to your email.",
            data={"expires_in": LOGIN_OTP_TTL}
        )


class PasswordResetRequestAPIView(APIView):
    """Request password reset token."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
            context={'tenant_id': str(tenant_id) if tenant_id else 'none'}
        )
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        tenant_str = str(tenant_id) if tenant_id else 'none'
        
        otp = generate_otp(length=6)
        cache_key = get_reset_password_key(tenant_str, email)
        cache.set(cache_key, hash_token(otp), timeout=PASSWORD_RESET_TTL)
        cache.set(f"{cache_key}:attempts", 0, timeout=PASSWORD_RESET_TTL)
        
        send_password_reset_otp_task.delay(email, otp, tenant_str)
        
        # Always return success to prevent email enumeration
        return success_response(message="If the email exists, a password reset OTP has been sent.")


class PasswordResetConfirmAPIView(APIView):
    """Confirm password reset with token."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
            context={'tenant_id': str(tenant_id) if tenant_id else 'none'}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        
        # Clear cache
        cache_key = get_reset_password_key(
            str(tenant_id) if tenant_id else 'none',
            user.email
        )
        cache.delete(cache_key)
        
        return success_response(message="Password reset successful. You can now login.")



class LogoutAPIView(APIView):
    """Logout by blacklisting refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Denylist access token for 30 minutes (matches access token lifetime)
            auth_header = request.META.get("HTTP_AUTHORIZATION")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ")[1]
                cache.set(f"denylist_{access_token}", True, timeout=ACCESS_TOKEN_DENYLIST_TTL)

            serializer = LogoutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            refresh_token = serializer.validated_data["refresh"]
            if blacklist_refresh_token(refresh_token):
                return success_response(message="Logout successful.")
            return error_response("Invalid refresh token.", status_code=http_status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)


class VerifyLoginOTPAPIView(APIView):
    """Verify login OTP and return JWT tokens (2FA Step 2) - Tenant Scoped."""
    permission_classes = [AllowAny]

    def post(self, request, tenant_id=None):
        serializer = VerifyLoginOTPSerializer(
            data=request.data,
            context={'tenant_id': str(tenant_id) if tenant_id else None}
        )
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Clear OTP from cache
        cache_key = get_login_otp_key(str(tenant_id) if tenant_id else 'none', user.email)
        cache.delete(cache_key)
        cache.delete(f"{cache_key}:attempts")
        
        return success_response(
            message="Login successful.",
            data={
                'access': serializer.validated_data['access'],
                'refresh': serializer.validated_data['refresh'],
            }
        )


class SuperAdminLoginAPIView(APIView):
    """Request login OTP for Super Admin (Step 1)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate and cache login OTP (Reserved tenant ID for super admin)
        otp = generate_otp(length=6)
        cache_key = get_login_otp_key('super-admin', user.email)
        cache.set(cache_key, hash_token(otp), timeout=LOGIN_OTP_TTL)
        cache.set(f"{cache_key}:attempts", 0, timeout=LOGIN_OTP_TTL)
        
        send_login_otp_task.delay(user.email, otp, None)
        
        return success_response(
            message="Super Admin Login OTP has been sent to your email.",
            data={"expires_in": LOGIN_OTP_TTL}
        )


class SuperAdminVerifyLoginOTPAPIView(APIView):
    """Verify login OTP and return JWT tokens for Super Admin (Step 2)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminVerifyLoginOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Clear OTP from cache
        cache_key = get_login_otp_key('super-admin', user.email)
        cache.delete(cache_key)
        cache.delete(f"{cache_key}:attempts")
        
        return success_response(
            message="Super Admin login successful.",
            data={
                'access': serializer.validated_data['access'],
                'refresh': serializer.validated_data['refresh'],
            }
        )
