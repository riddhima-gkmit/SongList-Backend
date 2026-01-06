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

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Username cannot be empty.")

        user = User.objects.filter(username=value).first()
        if user:
            if user.deleted_at:
                raise serializers.ValidationError("This account is disabled, please contact support.")
            raise serializers.ValidationError("Username already exists.")

        return value

    def validate_email(self, value):
        # Enforce strict email formatting using regex and lowercase conversion
        try:
            email = value.strip().lower()
            
            if not email:
                raise serializers.ValidationError("Email cannot be empty.")

            regex = r"^[a-z0-9._%+-]+@[a-z]+\.[a-z]{2,}$"
            
            if not re.match(regex, email):
                raise serializers.ValidationError("Invalid email format.")

            user = User.objects.filter(email=email).first()
            if user:
                if user.deleted_at:
                    raise serializers.ValidationError("This account is disabled, please contact support.")
                raise serializers.ValidationError("Email already registered.")
            
            return email

        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError("Invalid email format.")

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
            
        digits_count = sum(c.isdigit() for c in value)
        if digits_count < 7 or digits_count > 15:
            raise serializers.ValidationError("Phone number must contain between 7 and 15 digits.")

        return value

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
