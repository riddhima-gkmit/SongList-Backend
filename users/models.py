from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.utils import timezone

from common.enums import UserRole
from common.models import BaseModel

from common.constants import PHONE_MAX_LENGTH, ROLE_MAX_LENGTH

class UserManager(BaseUserManager):
    """
    Custom manager for User model.
    Handles user and superuser creation safely.
    """
    use_in_migrations = True

    def create_user(self, username, email, password=None, role=UserRole.USER, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        if not username:
            raise ValueError("Username is required")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            role=role,
            **extra_fields,
        )

        if password:
            try:
                validate_password(password, user=user)
            except DjangoValidationError as e:
                raise ValueError(
                    f"Password validation failed: {', '.join(e.messages)}"
                )
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        """
        Create superuser with ADMIN role.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(
            username=username,
            email=email,
            password=password,
            role=UserRole.ADMIN,
            **extra_fields,
        )


class User(AbstractUser, BaseModel):
    """
    Custom User model for SongList.
    """

    email = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=PHONE_MAX_LENGTH, blank=True)

    role = models.CharField(
        max_length=ROLE_MAX_LENGTH,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        """
        Soft delete the user.
        """
        self.deleted_at = timezone.now()
        self.is_active = False
        self.songs.update(deleted_at = timezone.now())
        self.playlists.update(deleted_at = timezone.now())
        self.save(update_fields=["deleted_at", "is_active"])

    @property
    def is_admin(self):
        """
        Check if user has ADMIN role.
        """
        return self.role == UserRole.ADMIN
