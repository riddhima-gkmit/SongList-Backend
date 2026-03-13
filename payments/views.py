"""
Payment views for payment link creation.
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.context import get_correlation_id
from common.pagination import DefaultPagination
from common.permissions import IsAdmin, IsSuperAdmin
from common.responses import error_response, success_response
from payments.models import PaymentTransaction, Subscription
from payments.serializers import (
    SubscriptionSerializer,
    SuperAdminPaymentTransactionSerializer,
    SuperAdminSubscriptionSerializer,
)
from payments.services import RazorpayService

logger = logging.getLogger(__name__)


class CreatePaymentLinkAPIView(APIView):
    """Create a Razorpay payment link for premium subscription."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return error_response("User has no tenant", status_code=status.HTTP_400_BAD_REQUEST)

            service = RazorpayService()
            user_email = request.user.email
            user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            
            transaction = service.create_payment_link(
                tenant=tenant,
                user_email=user_email,
                user_name=user_name if user_name else None,
            )

            logger.info(
                f"Payment link created for tenant {tenant.id}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "tenant_id": tenant.id,
                    "user_id": request.user.id,
                },
            )

            return success_response(
                "Payment link created successfully",
                {
                    "payment_link_id": transaction.razorpay_payment_link_id,
                    "payment_link_url": transaction.payment_link_url,
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                },
                status.HTTP_201_CREATED,
            )
        except ValueError as e:
            logger.warning(
                f"Payment link creation failed (validation): {e}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "tenant_id": request.user.tenant.id if request.user.tenant else None,
                },
            )
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                f"Error creating payment link: {e}",
                exc_info=True,
                extra={
                    "correlation_id": get_correlation_id(),
                    "tenant_id": request.user.tenant.id if request.user.tenant else None,
                },
            )
            return error_response(
                "Failed to create payment link", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubscriptionStatusAPIView(APIView):
    """Get tenant's subscription status."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return error_response("User has no tenant", status_code=status.HTTP_400_BAD_REQUEST)

            try:
                subscription = tenant.subscription
                data = SubscriptionSerializer(subscription).data
            except Subscription.DoesNotExist:
                data = {"is_premium": False, "activated_at": None, "source": ""}

            return success_response("Subscription status retrieved", data)
        except Exception as e:
            return error_response(
                "Failed to get subscription status", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuperAdminListSubscriptionsAPIView(APIView):
    """Super Admin endpoint to list all subscriptions across the platform."""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        """Get all subscriptions."""
        try:
            subscriptions = Subscription.objects.select_related('tenant', 'payment_transaction').order_by('-created_at')
            
            # Filter by tenant_id if provided
            tenant_id = request.query_params.get('tenant_id')
            if tenant_id:
                subscriptions = subscriptions.filter(tenant_id=tenant_id)
            
            # Filter by is_premium if provided
            is_premium = request.query_params.get('is_premium')
            if is_premium is not None:
                is_premium_bool = is_premium.lower() in ('true', '1', 'yes')
                subscriptions = subscriptions.filter(is_premium=is_premium_bool)
            
            # Paginate results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(subscriptions, request)
            
            serializer = SuperAdminSubscriptionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return error_response(
                "Failed to retrieve subscriptions", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuperAdminListPaymentsAPIView(APIView):
    """Super Admin endpoint to list all payment transactions across the platform."""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        """Get all payment transactions."""
        try:
            transactions = PaymentTransaction.objects.select_related('tenant').order_by('-created_at')
            
            # Filter by tenant_id if provided
            tenant_id = request.query_params.get('tenant_id')
            if tenant_id:
                transactions = transactions.filter(tenant_id=tenant_id)
            
            # Filter by status if provided
            payment_status = request.query_params.get('status')
            if payment_status:
                transactions = transactions.filter(status=payment_status)
            
            # Paginate results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(transactions, request)
            
            serializer = SuperAdminPaymentTransactionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return error_response(
                "Failed to retrieve payment transactions", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR
            )


