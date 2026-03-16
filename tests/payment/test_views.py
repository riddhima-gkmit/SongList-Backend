"""Integration tests for payment API views and webhook handler."""
import hashlib
import hmac
import json
import pytest
from unittest.mock import MagicMock

from django.urls import reverse

from common.enums import PaymentStatus
from payments.models import Subscription, WebhookEvent
from tests.factories.payment_factory import PaymentTransactionFactory, SubscriptionFactory
from tests.factories.tenant_factory import TenantFactory
from tests.factories.user_factory import AdminUserFactory, SuperAdminFactory, UserFactory


def _make_webhook_body_and_sig(payload: dict, secret: str = "test_webhook_secret") -> tuple[bytes, str]:
    """Return (body_bytes, valid_signature) for the given payload dict."""
    body = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


def _mock_transaction(link_id="plink_test", url="https://rzp.io/l/test", amount=999.0):
    """Build a minimal MagicMock that looks like a PaymentTransaction."""
    txn = MagicMock()
    txn.razorpay_payment_link_id = link_id
    txn.payment_link_url = url
    txn.amount = amount
    txn.currency = "INR"
    return txn


CREATE_LINK_URL = "/api/v1/payments/create-payment-link/"
SUBSCRIPTION_URL = "/api/v1/payments/subscription/"
SUPER_ADMIN_SUBS_URL = "/api/v1/payments/super-admin/subscriptions/"
SUPER_ADMIN_PAYMENTS_URL = "/api/v1/payments/super-admin/payments/"
WEBHOOK_URL = "/api/v1/payments/webhook/razorpay/"


@pytest.mark.django_db
class TestCreatePaymentLinkView:
    """POST /api/v1/payments/create-payment-link/ — requires ADMIN role."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(CREATE_LINK_URL)
        assert response.status_code == 401

    def test_super_admin_returns_403(self, super_admin_client):
        response = super_admin_client.post(CREATE_LINK_URL)
        assert response.status_code == 403

    def test_listener_returns_403(self, listener_client):
        response = listener_client.post(CREATE_LINK_URL)
        assert response.status_code == 403

    def test_admin_receives_payment_link_on_success(self, admin_client, mock_razorpay_service):
        """Service returns a mock transaction; view responds with 201 and link data."""
        mock_razorpay_service.create_payment_link.return_value = _mock_transaction()
        response = admin_client.post(CREATE_LINK_URL)
        assert response.status_code == 201
        assert response.data["data"]["payment_link_url"] == "https://rzp.io/l/test"

    def test_response_contains_required_keys(self, admin_client, mock_razorpay_service):
        mock_razorpay_service.create_payment_link.return_value = _mock_transaction()
        response = admin_client.post(CREATE_LINK_URL)
        data = response.data["data"]
        assert {"payment_link_id", "payment_link_url", "amount", "currency"} <= set(data.keys())

    def test_returns_400_when_service_raises_value_error(self, admin_client, mock_razorpay_service):
        """Already-premium tenants cause a ValueError which maps to 400."""
        mock_razorpay_service.create_payment_link.side_effect = ValueError("already premium")
        response = admin_client.post(CREATE_LINK_URL)
        assert response.status_code == 400

    def test_returns_500_when_service_raises_unexpected_error(self, admin_client, mock_razorpay_service):
        mock_razorpay_service.create_payment_link.side_effect = Exception("boom")
        response = admin_client.post(CREATE_LINK_URL)
        assert response.status_code == 500



@pytest.mark.django_db
class TestSubscriptionStatusView:
    """GET /api/v1/payments/subscription/ — requires ADMIN role."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(SUBSCRIPTION_URL)
        assert response.status_code == 401

    def test_super_admin_returns_403(self, super_admin_client):
        response = super_admin_client.get(SUBSCRIPTION_URL)
        assert response.status_code == 403

    def test_listener_returns_403(self, listener_client):
        response = listener_client.get(SUBSCRIPTION_URL)
        assert response.status_code == 403

    def test_admin_with_no_subscription_returns_free_status(self, admin_client):
        """Tenant without a Subscription record should return is_premium=False."""
        response = admin_client.get(SUBSCRIPTION_URL)
        assert response.status_code == 200
        assert response.data["data"]["is_premium"] is False

    def test_admin_with_premium_subscription_returns_true(self, admin_user, admin_client):
        SubscriptionFactory(tenant=admin_user.tenant, is_premium=True)
        response = admin_client.get(SUBSCRIPTION_URL)
        assert response.status_code == 200
        assert response.data["data"]["is_premium"] is True

    def test_response_contains_subscription_fields(self, admin_client):
        response = admin_client.get(SUBSCRIPTION_URL)
        assert {"is_premium", "activated_at", "source"} <= set(response.data["data"].keys())



@pytest.mark.django_db
class TestSuperAdminListSubscriptionsView:
    """GET /api/v1/payments/super-admin/subscriptions/ — requires SUPER_ADMIN."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(SUPER_ADMIN_SUBS_URL)
        assert response.status_code == 401

    def test_admin_returns_403(self, admin_client):
        response = admin_client.get(SUPER_ADMIN_SUBS_URL)
        assert response.status_code == 403

    def test_listener_returns_403(self, listener_client):
        response = listener_client.get(SUPER_ADMIN_SUBS_URL)
        assert response.status_code == 403

    def test_super_admin_gets_empty_list_when_no_subscriptions(self, super_admin_client):
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_returns_all_subscriptions(self, super_admin_client):
        SubscriptionFactory.create_batch(3)
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL)
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_filter_by_tenant_id(self, super_admin_client):
        tenant = TenantFactory()
        SubscriptionFactory(tenant=tenant)
        SubscriptionFactory.create_batch(2)
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL, {"tenant_id": str(tenant.id)})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert str(response.data["data"][0]["tenant_id"]) == str(tenant.id)

    def test_filter_by_is_premium_true(self, super_admin_client):
        SubscriptionFactory(is_premium=True)
        SubscriptionFactory(is_premium=False)
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL, {"is_premium": "true"})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["data"][0]["is_premium"] is True

    def test_filter_by_is_premium_false(self, super_admin_client):
        SubscriptionFactory(is_premium=True)
        SubscriptionFactory(is_premium=False)
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL, {"is_premium": "false"})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["data"][0]["is_premium"] is False

    def test_response_is_paginated(self, super_admin_client):
        SubscriptionFactory.create_batch(2)
        response = super_admin_client.get(SUPER_ADMIN_SUBS_URL)
        assert "data" in response.data
        assert "count" in response.data



@pytest.mark.django_db
class TestSuperAdminListPaymentsView:
    """GET /api/v1/payments/super-admin/payments/ — requires SUPER_ADMIN."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert response.status_code == 401

    def test_admin_returns_403(self, admin_client):
        response = admin_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert response.status_code == 403

    def test_listener_returns_403(self, listener_client):
        response = listener_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert response.status_code == 403

    def test_super_admin_gets_empty_list_when_no_transactions(self, super_admin_client):
        response = super_admin_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_returns_all_transactions(self, super_admin_client):
        PaymentTransactionFactory.create_batch(3)
        response = super_admin_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_filter_by_tenant_id(self, super_admin_client):
        tenant = TenantFactory()
        PaymentTransactionFactory(tenant=tenant)
        PaymentTransactionFactory.create_batch(2)
        response = super_admin_client.get(SUPER_ADMIN_PAYMENTS_URL, {"tenant_id": str(tenant.id)})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert str(response.data["data"][0]["tenant_id"]) == str(tenant.id)

    def test_filter_by_status(self, super_admin_client):
        PaymentTransactionFactory(status=PaymentStatus.ACTIVATED)
        PaymentTransactionFactory(status=PaymentStatus.CREATED)
        response = super_admin_client.get(SUPER_ADMIN_PAYMENTS_URL, {"status": "ACTIVATED"})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["data"][0]["status"] == "ACTIVATED"

    def test_response_is_paginated(self, super_admin_client):
        PaymentTransactionFactory.create_batch(2)
        response = super_admin_client.get(SUPER_ADMIN_PAYMENTS_URL)
        assert "data" in response.data
        assert "count" in response.data


@pytest.mark.django_db
class TestRazorpayWebhook:
    """POST /api/v1/payments/webhook/razorpay/ — no auth, signature-verified."""

    def test_missing_signature_returns_400(self, api_client):
        response = api_client.post(
            WEBHOOK_URL,
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_invalid_signature_returns_401(self, api_client):
        body = json.dumps({"event": "payment.captured"}).encode()
        response = api_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="bad_signature",
        )
        assert response.status_code == 401

    def test_valid_signature_returns_200(self, api_client):
        payload = {"event": "some.other.event", "account_id": "acc_test"}
        body, sig = _make_webhook_body_and_sig(payload)
        response = api_client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        assert response.status_code == 200

    def test_duplicate_webhook_is_accepted_without_reprocessing(self, api_client):
        """Second request with same payload returns 200 (idempotent)."""
        payload = {"event": "some.event", "account_id": "acc_1"}
        body, sig = _make_webhook_body_and_sig(payload)

        api_client.post(
            WEBHOOK_URL, data=body, content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        response = api_client.post(
            WEBHOOK_URL, data=body, content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Already processed"

    def test_webhook_event_is_stored_in_database(self, api_client):
        payload = {"event": "payment.captured", "account_id": "acc_store"}
        body, sig = _make_webhook_body_and_sig(payload)
        api_client.post(
            WEBHOOK_URL, data=body, content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        idempotency_key = hashlib.sha256(body).hexdigest()
        assert WebhookEvent.objects.filter(idempotency_key=idempotency_key).exists()

    def test_invalid_json_returns_400(self, api_client):
        bad_body = b"not json {"
        sig = hmac.new(b"test_webhook_secret", bad_body, hashlib.sha256).hexdigest()
        response = api_client.post(
            WEBHOOK_URL,
            data=bad_body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        assert response.status_code == 400
