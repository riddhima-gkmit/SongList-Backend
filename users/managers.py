"""User managers."""
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models

from common.enums import UserRole


class UserManager(BaseUserManager):
    """User manager."""
    use_in_migrations = True

    def get_queryset(self):
        """Filter deleted users."""
        return super().get_queryset().filter(deleted_at__isnull=True)

    def create_user(self, email, password=None, role=UserRole.LISTENER, tenant=None, **extra_fields):
        """Create user."""
        if not email:
            raise ValueError("Email is required")

        if role != UserRole.SUPER_ADMIN and not tenant:
            raise ValueError("Tenant is required for non-SUPER_ADMIN users")

        email = self.normalize_email(email)
        username = extra_fields.pop('username', email.split('@')[0])

        user = self.model(
            email=email,
            username=username,
            role=role,
            tenant=tenant,
            **extra_fields,
        )

        if password:
            try:
                validate_password(password, user=user)
            except DjangoValidationError as e:
                raise ValueError(f"Password validation failed: {', '.join(e.messages)}")
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create a superuser with SUPER_ADMIN role.
        Superusers do NOT belong to any tenant.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)

        return self.create_user(
            email=email,
            password=password,
            role=UserRole.SUPER_ADMIN,
            tenant=None,  # Superusers have no tenant
            **extra_fields,
        )


class AllUsersManager(BaseUserManager):
    """
    Manager that returns ALL users across all tenants.
    Used for admin operations and SUPER_ADMIN queries.
    """
    use_in_migrations = True

    def get_queryset(self):
        """Return all users without tenant filtering."""
        return super().get_queryset()
