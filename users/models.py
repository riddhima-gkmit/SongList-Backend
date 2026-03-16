from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.utils import timezone

from common.enums import UserRole
from common.models import SoftDeleteModel
from users.managers import UserManager, AllUsersManager


class User(AbstractUser, SoftDeleteModel):
    """User model."""
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )

    email = models.EmailField()
    phone_no = models.CharField(max_length=15, blank=True)

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.LISTENER,
    )

    is_verified = models.BooleanField(default=False)

    deleted_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_users'
    )

    # Managers
    objects = UserManager()  # Tenant-scoped manager
    all_users = AllUsersManager()  # Cross-tenant manager for SUPER_ADMIN

    # Username field for authentication (must be globally unique)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']  # Required for createsuperuser

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        constraints = [
            # Email must be unique per tenant
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                name='unique_email_per_tenant',
                condition=models.Q(tenant__isnull=False)
            ),
            # Email must be globally unique for SUPER_ADMIN (tenant is null)
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email_for_super_admin',
                condition=models.Q(tenant__isnull=True)
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'role']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @transaction.atomic
    def delete(self, using=None, keep_parents=False, deleted_by=None):
        """Soft delete user."""
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.is_active = False
        
        # Soft delete related objects
        self.songs.update(deleted_at=timezone.now())
        self.playlists.update(deleted_at=timezone.now())
        
        self.save(update_fields=["deleted_at", "deleted_by", "is_active", "updated_at"])

    def restore(self):
        """Restore user."""
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "deleted_by", "is_active"])

    @property
    def is_admin(self):
        """Check if admin."""
        return self.role == UserRole.ADMIN

    @property
    def is_super_admin(self):
        """Check if super admin."""
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_listener(self):
        """Check if listener."""
        return self.role == UserRole.LISTENER

    def clean(self):
        """Validate tenant."""
        super().clean()
        if self.role == UserRole.SUPER_ADMIN and self.tenant is not None:
            raise DjangoValidationError("SUPER_ADMIN users cannot belong to a tenant")
        if self.role != UserRole.SUPER_ADMIN and self.tenant is None:
            raise DjangoValidationError("LISTENER and ADMIN users must belong to a tenant")
