"""
Tenant model for multi-tenant architecture.
"""
from django.db import models
from common.models import SoftDeleteModel
from tenants.managers import ActiveTenantManager, AllTenantsManager


class Tenant(SoftDeleteModel):
    """
    Represents a tenant (organization) in the multi-tenant system.

    Managed by SUPER_ADMIN only.
    Premium status is tracked via Subscription model.
    """

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)

    # Managers
    objects = ActiveTenantManager()  # Default: only active, non-deleted tenants
    all_tenants = AllTenantsManager()  # All tenants including inactive/deleted (for SUPER_ADMIN)

    class Meta:
        db_table = "tenants"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='unique_tenant_name_active',
                condition=models.Q(deleted_at__isnull=True)
            ),
        ]

    def __str__(self):
        return self.name

    def activate(self):
        """Activate tenant."""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    def deactivate(self):
        """Deactivate tenant."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    @property
    def is_premium(self):
        """Check if tenant has active premium subscription."""
        try:
            return self.subscription.is_premium
        except Exception:
            return False

    @property
    def user_count(self):
        """Get number of active users in tenant."""
        return self.users.filter(deleted_at__isnull=True).count()
