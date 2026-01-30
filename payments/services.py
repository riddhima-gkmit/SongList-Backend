"""
Payment service layer.
All payment business logic is here, NOT in views.
"""
import time
import hashlib
import hmac
import logging
import uuid
from decimal import Decimal

import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.constants import PREMIUM_AMOUNT
from common.context import get_correlation_id
from common.enums import PaymentStatus
from payments.models import PaymentTransaction, Subscription, WebhookEvent
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class RazorpayService:
    """Service for Razorpay operations."""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_payment_link(
        self, tenant: Tenant, user_email: str = None, user_name: str = None
    ) -> PaymentTransaction:
        """Create a Razorpay payment link for premium subscription."""
        try:
            if tenant.is_premium:
                logger.warning(
                    f"Tenant {tenant.id} already has premium subscription",
                    extra={"correlation_id": get_correlation_id(), "tenant_id": tenant.id},
                )
                raise ValueError("Tenant already has premium subscription")

            # Check for existing pending transaction
            pending = PaymentTransaction.objects.filter(
                tenant=tenant,
                status__in=[
                    PaymentStatus.CREATED,
                    PaymentStatus.PENDING,
                    PaymentStatus.PAID,
                ],
            ).first()

            if pending and pending.payment_link_url:
                return pending

            # Create Razorpay payment link
            reference_id = f"premium_{uuid.uuid4().hex[:16]}"
            payment_link_data = {
                "amount": int(Decimal(str(PREMIUM_AMOUNT)) * 100),
                "currency": "INR",
                "description": f"Premium Subscription - {tenant.name}",
                "reference_id": reference_id,
                "expire_by": int(time.time()) + (16 * 60),
                "notes": {
                    "tenant_id": str(tenant.id),
                    "tenant_name": tenant.name,
                },
            }

            # Add customer details if provided
            if user_email:
                payment_link_data["customer"] = {
                    "email": user_email,
                }
                if user_name:
                    payment_link_data["customer"]["name"] = user_name

            # Create payment link
            payment_link = self.client.payment_link.create(data=payment_link_data)

            # Create transaction record
            # Store reference_id in metadata for webhook matching
            txn = PaymentTransaction.objects.create(
                tenant=tenant,
                razorpay_payment_link_id=payment_link["id"],
                payment_link_url=payment_link.get("short_url", ""),
                amount=Decimal(str(PREMIUM_AMOUNT)),
                currency="INR",
                status=PaymentStatus.CREATED,
                metadata={
                    "razorpay_payment_link": payment_link,
                    "reference_id": reference_id,  # Store for webhook matching
                },
            )

            logger.info(
                f"Created payment link for tenant {tenant.id}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "tenant_id": tenant.id,
                    "transaction_id": str(txn.id),
                },
            )

            return txn
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to create payment link: {e}",
                extra={"correlation_id": get_correlation_id(), "tenant_id": tenant.id},
            )
            raise ValueError(f"Failed to create payment link: {str(e)}")


    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature."""
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @transaction.atomic
    def process_payment_captured(self, event_data: dict) -> bool:
        """
        Process payment.captured or payment_link.paid webhook event.
        This is the source of truth for activating subscriptions.
        
        For payment links, Razorpay doesn't provide payment_link_id in webhook.
        We use tenant_id from notes (stored at creation) to find the transaction.
        """
        try:
            payload = event_data.get("payload", {})
            payment = payload.get("payment", {}).get("entity", {})
            order = payload.get("order", {}).get("entity", {})
            
            payment_id = payment.get("id")
            order_id = payment.get("order_id", {}) or order.get("id")
            
            if not payment_id:
                return False

            receipt = order.get("receipt")  # Contains reference_id like "premium_4a23481017b74040"
            
            # Razorpay stores reference_id in order.receipt
            txn = None
            if receipt:
                try:
                    txn = PaymentTransaction.objects.select_for_update().filter(
                        metadata__reference_id=receipt,
                        status__in=[PaymentStatus.CREATED, PaymentStatus.PENDING, PaymentStatus.PAID]
                    ).first()
                except Exception:
                    pass

            if not txn:
                logger.warning(
                    "Payment transaction not found for webhook payload",
                    extra={"correlation_id": get_correlation_id()},
                )
                return False

            # Store order_id for future lookups
            if order_id and not txn.razorpay_order_id:
                txn.razorpay_order_id = order_id

            # Skip if already activated (idempotent)
            if txn.status == PaymentStatus.ACTIVATED:
                return True

            # Update transaction
            if not txn.razorpay_payment_id:
                txn.razorpay_payment_id = payment_id

            txn.status = PaymentStatus.ACTIVATED
            txn.activated_at = timezone.now()
            txn.save()

            # Activate subscription
            subscription, _ = Subscription.objects.get_or_create(tenant=txn.tenant)
            subscription.activate(transaction=txn, source="razorpay")

            logger.info(
                f"Payment activated for tenant {txn.tenant_id} via webhook",
                extra={
                    "correlation_id": get_correlation_id(),
                    "transaction_id": str(txn.id),
                    "tenant_id": txn.tenant_id,
                },
            )

            return True
        except PaymentTransaction.DoesNotExist:
            logger.error(
                "Payment transaction not found for webhook",
                extra={"correlation_id": get_correlation_id()},
            )
            return False
        except Exception as e:
            logger.error(
                f"Error processing payment captured: {e}",
                exc_info=True,
                extra={"correlation_id": get_correlation_id()},
            )
            return False


class PaymentPollingService:
    """Service for payment reconciliation via polling."""

    def __init__(self):
        self.razorpay = RazorpayService()

    def reconcile_pending_payments(self):
        """Check status of pending payments via Razorpay API."""
        pending = PaymentTransaction.objects.filter(
            status__in=[
                PaymentStatus.CREATED,
                PaymentStatus.PENDING,
                PaymentStatus.PAID,
                PaymentStatus.VERIFIED,
            ]
        ).exclude(status=PaymentStatus.ACTIVATED)

        for txn in pending:
            self._check_transaction(txn)

    def _check_transaction(self, txn: PaymentTransaction):
        """Check single transaction status via API."""
        try:
            # Check payment link status
            if txn.razorpay_payment_link_id:
                payment_link = self.razorpay.client.payment_link.fetch(txn.razorpay_payment_link_id)
                
                if payment_link["status"] == "paid":
                    # For payment links, get order_id from payment_link and then get payments
                    order_id = payment_link.get("order_id")
                    if order_id:
                        # Get payments for the order
                        payments = self.razorpay.client.order.payments(order_id)
                        payment_items = payments.get("items", [])
                        
                        # Process first captured payment
                        for payment in payment_items:
                            if payment.get("status") == "captured":
                                # Construct webhook-like payload
                                self.razorpay.process_payment_captured({
                                    "payload": {
                                        "payment": {"entity": payment},
                                        "order": {"entity": {"id": order_id, "receipt": payment_link.get("reference_id")}}
                                    }
                                })
                                break
                
                elif payment_link["status"] in ["expired", "cancelled"]:
                    txn.mark_failed(f"Payment link {payment_link['status']}")
            
            # Fallback to order check for backward compatibility
            elif txn.razorpay_order_id:
                order = self.razorpay.client.order.fetch(txn.razorpay_order_id)

                if order["status"] == "paid":
                    payments = self.razorpay.client.order.payments(txn.razorpay_order_id)

                    for payment in payments.get("items", []):
                        if payment["status"] == "captured":
                            self.razorpay.process_payment_captured(
                                {"payload": {"payment": {"entity": payment}}}
                            )
                            break

                elif order["status"] == "expired":
                    txn.mark_failed("Order expired")
        except Exception as e:
            txn.error_message = str(e)
            txn.save(update_fields=["error_message", "updated_at"])
