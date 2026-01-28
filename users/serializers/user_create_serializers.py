"""
User creation serializers for admin and super admin.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from users.models import User
from tenants.models import Tenant
from common.enums import UserRole
from users.helpers.otp_token import generate_otp, hash_token
from users.helpers.cache_keys import get_verify_email_key
from common.constants import EMAIL_VERIFY_TTL, OTP_LENGTH
from django.core.cache import cache
from users.tasks import send_verification_otp_task


class UserCreateSerializer(serializers.Serializer):
    """Create user (ADMIN or LISTENER only)."""
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_no = serializers.CharField(max_length=15, required=False, allow_blank=True)
    tenant_id = serializers.UUIDField(required=False)  # Only for super admin
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def validate_email(self, value):
        # Check if email already exists
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_username(self, value):
        # Check if username already exists
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate(self, attrs):
        request = self.context['request']
        
        if request.user.role == UserRole.ADMIN:
            # Admin can only create LISTENER
            # Use admin's tenant
            if not request.user.tenant.is_active:
                raise serializers.ValidationError("Tenant is deactivated.")
            attrs['tenant'] = request.user.tenant
            attrs['role'] = UserRole.LISTENER
            
        elif request.user.role == UserRole.SUPER_ADMIN:
            # Super admin can only create ADMIN
            # Require tenant_id
            tenant_id = attrs.get('tenant_id')
            attrs['role'] = UserRole.ADMIN
            if not tenant_id:
                raise serializers.ValidationError("tenant_id is required for creating ADMIN users.")
            try:
                attrs['tenant'] = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise serializers.ValidationError("Invalid or inactive tenant.")
        
        return attrs
    
    def create(self, validated_data):
        tenant = validated_data.pop('tenant')
        validated_data.pop('tenant_id', None)
        
        user = User.objects.create_user(
            tenant=tenant,
            is_active=False,
            **validated_data
        )

        # Send verification email
        otp = generate_otp(length=OTP_LENGTH)
        cache_key = get_verify_email_key(str(tenant.id), user.email)
        cache.set(cache_key, hash_token(otp), timeout=EMAIL_VERIFY_TTL)
        cache.set(f"{cache_key}:attempts", 0, timeout=EMAIL_VERIFY_TTL)
        send_verification_otp_task.delay(str(user.id), otp, str(tenant.id))
        
        return user
