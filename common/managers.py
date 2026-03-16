"""Soft delete managers."""
from django.db import models


class SoftDeleteManager(models.Manager):
    """Manager for soft-deleted models."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def with_deleted(self):
        """Include soft-deleted records."""
        return super().get_queryset()

    def all_with_deleted(self):
        """Get all records including deleted."""
        return super().get_queryset()
