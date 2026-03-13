import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from ..models import User
from common.constants import PHONE_NUMBER_DIGITS


# User (Self) Serializers
class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for returning the authenticated user's profile.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_no",
            "role",
            "date_joined",
        ]
        read_only_fields = ["id", "role", "date_joined", "email"]

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name cannot be empty or just whitespace.")
        if not re.match(r"^[a-zA-Z\s]+$", value):
            raise serializers.ValidationError("First name can contain only letters and spaces.")
        return value

    def validate_last_name(self, value):
        if not value:
            return value
        value = value.strip()
        if not re.match(r"^[a-zA-Z\s]+$", value):
            raise serializers.ValidationError("Last name can contain only letters and spaces.")
        return value

    def validate_phone_no(self, value):
        # Validate phone number format (digits, spaces, hyphens, leading +)
        if not value:
            return value
        
        value = value.strip()
        
        if not value:
            raise serializers.ValidationError("Phone number cannot be empty or just whitespace.")
            
        if not re.match(r"^\+?[\d\s-]+$", value):
            raise serializers.ValidationError(
                "Phone number can only contain digits, spaces, hyphens, and a leading plus."
            )
        if value.startswith("0"):
            value = value[1:]
            
        if value.startswith("+91"):
            value = value[3:]
        elif value.startswith("+"):
            value = value[1:]

        digits_count = sum(c.isdigit() for c in value)
        if digits_count != PHONE_NUMBER_DIGITS:
            raise serializers.ValidationError(f"Phone number must contain {PHONE_NUMBER_DIGITS} digits.")
        
        normalized_phone = "+91" + value
        return normalized_phone

    def validate_username(self, value):
        """Ensure username is unique within tenant when updating."""
        if not value:
            raise serializers.ValidationError("Username cannot be empty.")
        
        value = value.strip()
        
        # Get the current user instance (if updating) or request user
        user = self.instance if self.instance else None
        request = self.context.get('request')
        
        if user and request:
            # Check if username is being changed
            if user.username != value:
                # Check for existing username in the same tenant
                existing_user = User.objects.filter(
                    username=value,
                    tenant=user.tenant,
                    deleted_at__isnull=True
                ).exclude(id=user.id).first()
                
                if existing_user:
                    raise serializers.ValidationError(
                        "A user with this username already exists in your organization."
                    )
        
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for allowing users to change their own password.
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value



# Admin Serializers
class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for Admin user management APIs.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_no",
            "role",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "role",
            "date_joined",
        ]


class SuperAdminAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for Super Admin to view all admins across platform.
    Includes tenant information.
    """
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_is_active = serializers.BooleanField(source="tenant.is_active", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_no",
            "role",
            "is_active",
            "is_verified",
            "date_joined",
            "tenant_id",
            "tenant_name",
            "tenant_is_active",
        ]
        read_only_fields = fields


