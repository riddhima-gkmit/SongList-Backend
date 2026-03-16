"""
Razorpay webhook handler.
Webhooks are the source of truth for payment status.
"""
import hashlib
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.context import get_correlation_id
from payments.models import WebhookEvent
from payments.services import RazorpayService
from payments.tasks import process_payment_webhook

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Handle Razorpay webhook events.
    - Verifies signature
    - Ensures idempotency
    - Processes event
    """
    try:
        service = RazorpayService()

        # Get signature
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not signature:
            return JsonResponse(
                {"status": "error", "message": "Missing signature"}, status=400
            )

        # Verify signature
        if not service.verify_webhook_signature(request.body, signature):
            logger.error(
                "Webhook signature verification failed",
                extra={"correlation_id": get_correlation_id()},
            )
            return JsonResponse(
                {"status": "error", "message": "Invalid signature"}, status=401
            )

        # Parse payload
        payload = json.loads(request.body)

        # Extract event info
        event_type = payload.get("event", "unknown")
        account_id = payload.get("account_id", "")

        # Create idempotency key from payload hash
        idempotency_key = hashlib.sha256(request.body).hexdigest()

        # Check for duplicate
        if WebhookEvent.objects.filter(idempotency_key=idempotency_key).exists():
            logger.info(
                f"Duplicate webhook event {event_type}, skipping",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_type": event_type,
                    "idempotency_key": idempotency_key[:20],
                },
            )
            return JsonResponse({"status": "success", "message": "Already processed"})

        # Store event
        webhook_event = WebhookEvent.objects.create(
            razorpay_event_id=f"{account_id}_{idempotency_key[:20]}",
            event_type=event_type,
            payload=payload,
            signature=signature,
            signature_verified=True,
            idempotency_key=idempotency_key,
        )

        logger.info(
            f"Received webhook: {event_type}",
            extra={
                "correlation_id": get_correlation_id(),
                "event_type": event_type,
                "webhook_event_id": str(webhook_event.id),
            },
        )

        # Process event asynchronously using Celery
        if event_type in ["payment.captured", "order.paid"]:
            process_payment_webhook.delay(str(webhook_event.id))
            logger.info(
                f"Queued webhook processing for event {event_type}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_type": event_type,
                    "webhook_event_id": str(webhook_event.id),
                },
            )
        else:
            webhook_event.mark_processed()
            logger.info(
                f"Ignoring webhook event type: {event_type}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_type": event_type,
                },
            )

        # Return success response immediately
        # Razorpay expects a quick response (within 5 seconds)
        # Actual processing happens asynchronously
        return JsonResponse({"status": "success"})

    except json.JSONDecodeError:
        logger.error(
            "Invalid JSON in webhook payload",
            extra={"correlation_id": get_correlation_id()},
        )
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"}, status=400
        )
    except Exception as e:
        logger.error(
            f"Error processing webhook: {e}",
            exc_info=True,
            extra={"correlation_id": get_correlation_id()},
        )
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
