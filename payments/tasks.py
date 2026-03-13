"""
Celery task for payment polling and reconciliation.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.db import close_old_connections
from django.utils import timezone

from common.context import get_correlation_id
from common.enums import PaymentStatus
from payments.models import PaymentTransaction, WebhookEvent
from payments.services import PaymentPollingService, RazorpayService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def poll_pending_payments(self):
    """
    Poll pending payment transactions for status updates.
    
    This task runs periodically to reconcile payments that may have
    missed webhook notifications. Uses same logic as PaymentPollingService
    (CREATED, PENDING, PAID, VERIFIED - no time filter).
    """
    close_old_connections()  # Ensure fresh DB connection in Celery worker
    try:
        # Same query as PaymentPollingService.reconcile_pending_payments
        pending_transactions = list(
            PaymentTransaction.objects.filter(
                status__in=[
                    PaymentStatus.CREATED,
                    PaymentStatus.PENDING,
                    PaymentStatus.PAID,
                    PaymentStatus.VERIFIED,
                ]
            )
            .exclude(status=PaymentStatus.ACTIVATED)
            .select_related("tenant")
        )
        
        polling_service = PaymentPollingService()
        reconciled_count = 0
        failed_count = 0
        
        # Process all pending transactions
        for transaction in pending_transactions:
            try:
                # Check individual transaction status
                polling_service._check_transaction(transaction)
                
                # Refresh to get updated status
                transaction.refresh_from_db()
                if transaction.status in [PaymentStatus.PAID, PaymentStatus.VERIFIED, PaymentStatus.ACTIVATED]:
                    reconciled_count += 1
                    link_id = transaction.razorpay_payment_link_id or transaction.razorpay_order_id
                    logger.info(
                        f"Reconciled payment {link_id}: {transaction.status}",
                        extra={
                            "correlation_id": get_correlation_id(),
                            "transaction_id": str(transaction.id),
                        },
                    )
            except Exception as e:
                failed_count += 1
                link_id = transaction.razorpay_payment_link_id or transaction.razorpay_order_id
                logger.error(
                    f"Failed to poll payment {link_id}: {str(e)}",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "transaction_id": str(transaction.id),
                    },
                )

        logger.info(
            f"Payment polling complete: {reconciled_count} reconciled, "
            f"{failed_count} failed",
            extra={
                "correlation_id": get_correlation_id(),
                "reconciled_count": reconciled_count,
                "failed_count": failed_count,
            },
        )
        
        return {
            "total": len(pending_transactions),
            "reconciled": reconciled_count,
            "failed": failed_count,
        }
        
    except Exception as exc:
        logger.error(
            f"Payment polling task failed: {str(exc)}",
            exc_info=True,
            extra={"correlation_id": get_correlation_id()},
        )
        raise self.retry(exc=exc, countdown=60)  # Retry after 1 minute


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_payment_webhook(self, webhook_event_id):
    """
    Process payment webhook event asynchronously.
    
    This task processes payment.captured and order.paid events
    to activate subscriptions. Runs in background to ensure
    quick response to Razorpay.
    
    Args:
        webhook_event_id: UUID of WebhookEvent to process
    """
    try:
        logger.info(
            f"Processing webhook event {webhook_event_id}",
            extra={
                "correlation_id": get_correlation_id(),
                "webhook_event_id": webhook_event_id,
            },
        )

        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)

        # Skip if already processed
        if webhook_event.processed:
            logger.info(
                f"Webhook event {webhook_event_id} already processed",
                extra={
                    "correlation_id": get_correlation_id(),
                    "webhook_event_id": webhook_event_id,
                },
            )
            return {"status": "already_processed"}

        event_type = webhook_event.event_type
        payload = webhook_event.payload
        
        # Only process payment-related events
        if event_type not in ["payment.captured", "order.paid"]:
            logger.info(
                f"Skipping non-payment event: {event_type}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_type": event_type,
                },
            )
            webhook_event.mark_processed()
            return {'status': 'skipped', 'event_type': event_type}
        
        # Process payment
        service = RazorpayService()
        success = service.process_payment_captured(payload)
        
        if success:
            webhook_event.mark_processed()
            logger.info(
                f"Successfully processed webhook event {webhook_event_id}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "webhook_event_id": webhook_event_id,
                },
            )
            return {"status": "success", "event_type": event_type}
        else:
            logger.warning(
                f"Failed to process webhook event {webhook_event_id}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "webhook_event_id": webhook_event_id,
                },
            )
            # Retry if processing failed
            raise Exception(f"Payment processing failed for event {webhook_event_id}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(
            f"WebhookEvent {webhook_event_id} not found",
            extra={
                "correlation_id": get_correlation_id(),
                "webhook_event_id": webhook_event_id,
            },
        )
        return {"status": "error", "message": "WebhookEvent not found"}
    except Exception as exc:
        logger.error(
            f"Error processing webhook event {webhook_event_id}: {str(exc)}",
            exc_info=True,
            extra={
                "correlation_id": get_correlation_id(),
                "webhook_event_id": webhook_event_id,
            },
        )
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task
def cleanup_old_webhook_events():
    """
    Clean up old webhook events to prevent database bloat.
    Keeps events for 30 days.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = WebhookEvent.objects.filter(
            created_at__lte=cutoff_date
        ).delete()
        
        logger.info(
            f"Cleaned up {deleted_count} old webhook events",
            extra={
                "correlation_id": get_correlation_id(),
                "deleted_count": deleted_count,
            },
        )
        return {"deleted": deleted_count}

    except Exception as exc:
        logger.error(
            f"Webhook cleanup task failed: {str(exc)}",
            exc_info=True,
            extra={"correlation_id": get_correlation_id()},
        )
        raise
