import re
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from ..models import User


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
        read_only_fields = ["id", "role", "date_joined"]

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

        digits_count = sum(c.isdigit() for c in value)
        if digits_count < 10 or digits_count > 10:
            raise serializers.ValidationError("Phone number must contain 10 digits.")
        
        normalized_phone = "+91" + value


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
            "first_name",
            "last_name",
            "phone_no",
            "date_joined",
        ]

    
    