"""Tenant managers."""
from django.db import models


class ActiveTenantManager(models.Manager):
    """
    Manager that returns only active, non-deleted tenants.
    """
    use_in_migrations = True

    def get_queryset(self):
        """Filter to only active, non-deleted tenants."""
        return super().get_queryset().filter(
            deleted_at__isnull=True,
            is_active=True
        )


class AllTenantsManager(models.Manager):
    """
    Manager that returns all tenants including inactive and deleted ones.
    """
    use_in_migrations = True

    def get_queryset(self):
        """Return all tenants without filtering."""
        return super().get_queryset()
