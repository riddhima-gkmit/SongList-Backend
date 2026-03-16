"""
Payment URLs.
"""
from django.urls import path
from payments.views import (
    CreatePaymentLinkAPIView,
    SubscriptionStatusAPIView,
    SuperAdminListSubscriptionsAPIView,
    SuperAdminListPaymentsAPIView,
)
from payments.webhooks import razorpay_webhook

urlpatterns = [
    path("create-payment-link/", CreatePaymentLinkAPIView.as_view(), name="create-payment-link"),
    path("subscription/", SubscriptionStatusAPIView.as_view(), name="subscription-status"),
    path("webhook/razorpay/", razorpay_webhook, name="razorpay-webhook"),
    # Super Admin endpoints
    path("super-admin/subscriptions/", SuperAdminListSubscriptionsAPIView.as_view(), name="super-admin-list-subscriptions"),
    path("super-admin/payments/", SuperAdminListPaymentsAPIView.as_view(), name="super-admin-list-payments"),
]
