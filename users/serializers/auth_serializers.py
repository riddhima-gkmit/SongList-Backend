import re

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from tenants.models import Tenant
from users.models import User
from users.helpers import (
    verify_token,
    get_verify_email_key,
    get_reset_password_key,
    get_login_otp_key,
)

from common.constants import (
    EMAIL_VERIFY_TTL,
    OTP_LENGTH,
)



class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_no = serializers.CharField(required=False, allow_blank=True)

    def validate_phone_no(self, value):
        if not value:
            return value
        value = value.strip()
        if not re.fullmatch(r"\d{10}", value):
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")

        return f"+91{value}"

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        validate_password(attrs["password"])
        attrs.pop("confirm_password")
        return attrs

class VerifyEmailSerializer(serializers.Serializer):
    """Verify user email with OTP."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=OTP_LENGTH, min_length=OTP_LENGTH)

    def validate(self, attrs):
        from common.constants import MAX_OTP_ATTEMPTS
        
        email = attrs['email']
        otp = attrs['otp']
        tenant_id = self.context.get('tenant_id', 'none')
        try:
            user = User.objects.get(email=email, tenant_id=tenant_id if tenant_id != 'none' else None)
            if user.is_verified:
                raise serializers.ValidationError("This account is already verified")
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if not Tenant.objects.filter(id=tenant_id).exists():
            raise serializers.ValidationError("Tenant not found.")
        cache_key = get_verify_email_key(tenant_id, email)
        attempts_key = f"{cache_key}:attempts"
        
        # Check attempt limit
        attempts = cache.get(attempts_key, 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            raise serializers.ValidationError("Maximum OTP attempts exceeded. Please request a new OTP.")
        
        cached_hash = cache.get(cache_key)
        
        if not cached_hash or not verify_token(otp, cached_hash):
            # Increment attempt counter
            cache.set(attempts_key, attempts + 1, timeout=EMAIL_VERIFY_TTL)
            remaining = MAX_OTP_ATTEMPTS - (attempts + 1)
            raise serializers.ValidationError(
                f"Invalid or expired OTP. {remaining} attempt(s) remaining."
            )
        
        
        attrs['user'] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    """Request login OTP with email and password (2FA Step 1) - Tenant Scoped."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        tenant_id = self.context.get('tenant_id')
        if not Tenant.objects.filter(id=tenant_id).exists():
            raise serializers.ValidationError("Tenant not found.")
        if not tenant_id:
            raise serializers.ValidationError("Tenant ID is required for regular login.")
            
        # Find user by email AND tenant
        user = User.all_users.filter(
            email=email,
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).first()
        
        # Regular login does NOT allow super admin login
        if user and user.is_superuser:
            raise serializers.ValidationError("Super admins must use the dedicated super admin login endpoint.")
            
        # Generic error to prevent user enumeration
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.is_verified:
            raise serializers.ValidationError(
                "Email not verified. Please verify your email before logging in."
            )
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        attrs['user'] = user
        return attrs


class SuperAdminLoginSerializer(serializers.Serializer):
    """Request login OTP for Super Admin (Step 1)."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Find user by email (Super Admins are NOT tenant-scoped in the same way)
        user = User.all_users.filter(
            email=email,
            deleted_at__isnull=True,
            is_superuser=True
        ).first()
        
        # Generic error
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials or user is not a super admin.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        attrs['user'] = user
        return attrs



class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset token."""
    email = serializers.EmailField()

    def validate_email(self, value):
        tenant_id = self.context.get('tenant_id', 'none')
        if not Tenant.objects.filter(id=tenant_id).exists():
            raise serializers.ValidationError("Tenant not found.")
        try:
            user = User.objects.get(email=value, tenant_id=tenant_id if tenant_id != 'none' else None)
        except User.DoesNotExist:
            # Don't reveal if email exists
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Reset password with OTP."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=OTP_LENGTH, min_length=OTP_LENGTH)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from common.constants import MAX_OTP_ATTEMPTS, PASSWORD_RESET_TTL
        
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        email = attrs['email']
        otp = attrs['otp']
        tenant_id = self.context.get('tenant_id', 'none')
        if not Tenant.objects.filter(id=tenant_id).exists():
            raise serializers.ValidationError("Tenant not found.")
        cache_key = get_reset_password_key(tenant_id, email)
        attempts_key = f"{cache_key}:attempts"
        
        # Check attempt limit
        attempts = cache.get(attempts_key, 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            raise serializers.ValidationError("Maximum OTP attempts exceeded. Please request a new OTP.")
        
        cached_hash = cache.get(cache_key)
        
        if not cached_hash or not verify_token(otp, cached_hash):
            # Increment attempt counter
            cache.set(attempts_key, attempts + 1, timeout=PASSWORD_RESET_TTL)
            remaining = MAX_OTP_ATTEMPTS - (attempts + 1)
            raise serializers.ValidationError(
                f"Invalid or expired OTP. {remaining} attempt(s) remaining."
            )
        
        try:
            user = User.objects.get(email=email, tenant_id=tenant_id if tenant_id != 'none' else None)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        attrs['user'] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Logout by blacklisting refresh token."""
    refresh = serializers.CharField()




class VerifyLoginOTPSerializer(serializers.Serializer):
    """Verify login OTP and authenticate user (2FA Step 2) - Tenant Scoped."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=OTP_LENGTH, min_length=OTP_LENGTH)

    def validate(self, attrs):
        from common.constants import LOGIN_OTP_TTL, MAX_OTP_ATTEMPTS
        
        email = attrs['email']
        otp = attrs['otp']
        tenant_id = self.context.get('tenant_id', 'none')

        if not Tenant.objects.filter(id=tenant_id).exists():
            raise serializers.ValidationError("Tenant not found.")
        cache_key = get_login_otp_key(tenant_id, email)
        attempts_key = f"{cache_key}:attempts"
        
        # Check attempt limit
        attempts = cache.get(attempts_key, 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            raise serializers.ValidationError("Maximum OTP attempts exceeded. Please request a new OTP.")
        
        cached_hash = cache.get(cache_key)
        
        if not cached_hash or not verify_token(otp, cached_hash):
            # Increment attempt counter
            cache.set(attempts_key, attempts + 1, timeout=LOGIN_OTP_TTL)
            remaining = MAX_OTP_ATTEMPTS - (attempts + 1)
            raise serializers.ValidationError(
                f"Invalid or expired OTP. {remaining} attempt(s) remaining."
            )
        
        try:
            user = User.all_users.filter(
                email=email,
                tenant_id=tenant_id if tenant_id != 'none' else None,
                deleted_at__isnull=True
            ).first()
            
            if not user or user.is_superuser:
                raise User.DoesNotExist
                
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found or scope mismatch.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        if not user.is_verified:
            raise serializers.ValidationError("Please verify your email before logging in.")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        attrs['user'] = user
        attrs['access'] = str(refresh.access_token)
        attrs['refresh'] = str(refresh)
        return attrs


class SuperAdminVerifyLoginOTPSerializer(serializers.Serializer):
    """Verify login OTP and authenticate Super Admin (Step 2)."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=OTP_LENGTH, min_length=OTP_LENGTH)

    def validate(self, attrs):
        from common.constants import LOGIN_OTP_TTL, MAX_OTP_ATTEMPTS
        
        email = attrs['email']
        otp = attrs['otp']
        # Special tenant ID for super admins in cache
        tenant_id = 'super-admin'
        
        cache_key = get_login_otp_key(tenant_id, email)
        attempts_key = f"{cache_key}:attempts"
        
        # Check attempt limit
        attempts = cache.get(attempts_key, 0)
        if attempts >= MAX_OTP_ATTEMPTS:
            raise serializers.ValidationError("Maximum OTP attempts exceeded. Please request a new OTP.")
        
        cached_hash = cache.get(cache_key)
        
        if not cached_hash or not verify_token(otp, cached_hash):
            # Increment attempt counter
            cache.set(attempts_key, attempts + 1, timeout=LOGIN_OTP_TTL)
            remaining = MAX_OTP_ATTEMPTS - (attempts + 1)
            raise serializers.ValidationError(
                f"Invalid or expired OTP. {remaining} attempt(s) remaining."
            )
        
        try:
            user = User.all_users.filter(
                email=email,
                is_superuser=True,
                deleted_at__isnull=True
            ).first()
            
            if not user:
                raise User.DoesNotExist
                
        except User.DoesNotExist:
            raise serializers.ValidationError("Super Admin user not found.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        attrs['user'] = user
        attrs['access'] = str(refresh.access_token)
        attrs['refresh'] = str(refresh)
        return attrs
