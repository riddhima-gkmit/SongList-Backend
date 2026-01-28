"""
Payment models for Razorpay integration.

Payment State Machine:
CREATED → PENDING → PAID → VERIFIED → ACTIVATED
                  ↘ FAILED
"""
from django.db import models
from django.utils import timezone
from common.models import BaseModel
from common.enums import PaymentStatus


class PaymentTransaction(BaseModel):
    """Payment transaction record."""

    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="payment_transactions"
    )

    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)  # Deprecated, kept for migration
    razorpay_payment_link_id = models.CharField(max_length=100, unique=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    payment_link_url = models.URLField(blank=True)  # Short URL from Razorpay

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self):
        link_id = self.razorpay_payment_link_id or self.razorpay_order_id
        return f"{self.tenant.name}: {link_id} ({self.status})"

    def mark_paid(self, payment_id: str):
        """Mark transaction as paid."""
        self.razorpay_payment_id = payment_id
        self.status = PaymentStatus.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["razorpay_payment_id", "status", "paid_at", "updated_at"])

    def mark_verified(self, signature: str):
        """Mark transaction as verified."""
        self.razorpay_signature = signature
        self.status = PaymentStatus.VERIFIED
        self.verified_at = timezone.now()
        self.save(update_fields=["razorpay_signature", "status", "verified_at", "updated_at"])

    def mark_activated(self):
        """Mark transaction as activated."""
        self.status = PaymentStatus.ACTIVATED
        self.activated_at = timezone.now()
        self.save(update_fields=["status", "activated_at", "updated_at"])

    def mark_failed(self, error_message: str):
        """Mark transaction as failed."""
        self.status = PaymentStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])


class Subscription(BaseModel):
    """
    Tenant subscription record.
    This is the ONLY place where is_premium is tracked.
    """

    tenant = models.OneToOneField(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="subscription"
    )
    is_premium = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=50, blank=True)

    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    class Meta:
        db_table = "subscriptions"

    def __str__(self):
        status = "Premium" if self.is_premium else "Free"
        return f"{self.tenant.name}: {status}"

    def activate(self, transaction=None, source="razorpay"):
        """Activate premium subscription."""
        self.is_premium = True
        self.activated_at = timezone.now()
        self.source = source
        self.payment_transaction = transaction
        self.save()


class WebhookEvent(BaseModel):
    """Razorpay webhook event log for audit and idempotency."""

    razorpay_event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField()
    signature = models.CharField(max_length=255)
    signature_verified = models.BooleanField(default=False)

    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    error_message = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        db_table = "webhook_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type}: {self.razorpay_event_id}"

    def mark_processed(self):
        """Mark event as successfully processed."""
        self.processed = True
        self.processed_at = timezone.now()
        self.save(update_fields=["processed", "processed_at", "updated_at"])

    def mark_failed(self, error: str):
        """Mark event as failed."""
        self.error_message = error
        self.save(update_fields=["error_message", "updated_at"])
