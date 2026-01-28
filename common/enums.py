"""
Enums for the SongList application.
"""
from django.db import models


class UserRole(models.TextChoices):
    """User roles for permission control."""
    LISTENER = "LISTENER", "Listener"
    ADMIN = "ADMIN", "Admin"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


class SongVisibility(models.TextChoices):
    """Song ownership type - GLOBAL (platform) or TENANT (local)."""
    GLOBAL = "GLOBAL", "Global"
    TENANT = "TENANT", "Tenant"


class PaymentStatus(models.TextChoices):
    """Payment transaction status."""
    CREATED = "CREATED", "Created"
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    VERIFIED = "VERIFIED", "Verified"
    ACTIVATED = "ACTIVATED", "Activated"
    FAILED = "FAILED", "Failed"

class RequestStatus(models.TextChoices):
    """Status of a song request"""
    PENDING = 'PENDING', 'Pending Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    FULFILLED = 'FULFILLED', 'Fulfilled'