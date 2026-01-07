import re
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User
from common.enums import UserRole


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles user registration with validation.
    """

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_no",
        ]

    def validate_first_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("First name cannot be empty.")

        if not re.match(r"^[a-zA-Z\s]+$", value):
            raise serializers.ValidationError(
                "First name can contain only letters and spaces."
            )

        return value

    def validate_last_name(self, value):
        if not value:
            return value

        value = value.strip()

        if not re.match(r"^[a-zA-Z\s]+$", value):
            raise serializers.ValidationError(
                "Last name can contain only letters and spaces."
            )

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
        
        # Check if phone number already exists
        if User.objects.filter(phone_no=normalized_phone).exists():
            raise serializers.ValidationError("Phone number already registered.")
        
        return normalized_phone

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """
        Create a regular USER.
        """
        if "confirm_password" in validated_data:
            validated_data.pop("confirm_password")

        return User.objects.create_user(
            role=UserRole.USER,
            **validated_data
        )


class LoginSerializer(serializers.Serializer):
    """
    Authenticates user and returns JWT tokens.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username", "").strip()
        password = attrs.get("password")

        if not username or not password:
            raise serializers.ValidationError(
                "Username and password are required."
            )

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError(
                "Invalid username or password."
            )

        if not user.is_active or user.deleted_at:
            raise serializers.ValidationError(
                "Account is inactive."
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class LogoutSerializer(serializers.Serializer):
    """
    Handles logout by blacklisting refresh token.
    """
    refresh = serializers.CharField()
