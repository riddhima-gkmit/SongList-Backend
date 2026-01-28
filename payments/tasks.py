"""
Celery task for payment polling and reconciliation.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from payments.services import PaymentPollingService, RazorpayService
from payments.models import PaymentTransaction, WebhookEvent
from common.enums import PaymentStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def poll_pending_payments(self):
    """
    Poll pending payment transactions for status updates.
    
    This task runs periodically to reconcile payments that may have
    missed webhook notifications.
    """
    try:
        # Get pending transactions older than 5 minutes
        cutoff_time = timezone.now() - timedelta(minutes=5)
        
        pending_transactions = PaymentTransaction.objects.filter(
            status=PaymentStatus.CREATED,
            created_at__lte=cutoff_time
        ).select_related('tenant', 'user')
        
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
                        f"Reconciled payment {link_id}: {transaction.status}"
                    )
            except Exception as e:
                failed_count += 1
                link_id = transaction.razorpay_payment_link_id or transaction.razorpay_order_id
                logger.error(
                    f"Failed to poll payment {link_id}: {str(e)}"
                )
        
        logger.info(
            f"Payment polling complete: {reconciled_count} reconciled, "
            f"{failed_count} failed"
        )
        
        return {
            'total': pending_transactions.count(),
            'reconciled': reconciled_count,
            'failed': failed_count
        }
        
    except Exception as exc:
        logger.error(f"Payment polling task failed: {str(exc)}")
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
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Skip if already processed
        if webhook_event.processed:
            logger.info(f"Webhook event {webhook_event_id} already processed")
            return {'status': 'already_processed'}
        
        event_type = webhook_event.event_type
        payload = webhook_event.payload
        
        # Only process payment-related events
        if event_type not in ["payment.captured", "order.paid"]:
            logger.info(f"Skipping non-payment event: {event_type}")
            webhook_event.mark_processed()
            return {'status': 'skipped', 'event_type': event_type}
        
        # Process payment
        service = RazorpayService()
        success = service.process_payment_captured(payload)
        
        if success:
            webhook_event.mark_processed()
            logger.info(f"Successfully processed webhook event {webhook_event_id}")
            return {'status': 'success', 'event_type': event_type}
        else:
            logger.warning(f"Failed to process webhook event {webhook_event_id}")
            # Retry if processing failed
            raise Exception(f"Payment processing failed for event {webhook_event_id}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"WebhookEvent {webhook_event_id} not found")
        return {'status': 'error', 'message': 'WebhookEvent not found'}
    except Exception as exc:
        logger.error(f"Error processing webhook event {webhook_event_id}: {str(exc)}")
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
        
        logger.info(f"Cleaned up {deleted_count} old webhook events")
        return {'deleted': deleted_count}
        
    except Exception as exc:
        logger.error(f"Webhook cleanup task failed: {str(exc)}")
        raise
