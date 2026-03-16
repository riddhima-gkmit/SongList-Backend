"""Tests for payment app serializers."""
import pytest

from payments.serializers import (
    PaymentTransactionSerializer,
    SubscriptionSerializer,
    SuperAdminPaymentTransactionSerializer,
    SuperAdminSubscriptionSerializer,
)
from tests.factories.payment_factory import (
    PaymentTransactionFactory,
    SubscriptionFactory,
)
from tests.factories.tenant_factory import TenantFactory


@pytest.mark.django_db
class TestPaymentTransactionSerializer:
    """PaymentTransactionSerializer exposes the correct fields and values."""

    def test_contains_expected_fields(self):
        txn = PaymentTransactionFactory()
        data = PaymentTransactionSerializer(txn).data
        expected = {
            "id", "razorpay_payment_link_id", "payment_link_url",
            "razorpay_payment_id", "amount", "currency", "status",
            "created_at", "paid_at", "activated_at",
        }
        assert expected == set(data.keys())

    def test_status_value_matches_model(self):
        txn = PaymentTransactionFactory()
        data = PaymentTransactionSerializer(txn).data
        assert data["status"] == txn.status

    def test_currency_is_inr(self):
        txn = PaymentTransactionFactory(currency="INR")
        data = PaymentTransactionSerializer(txn).data
        assert data["currency"] == "INR"

    def test_amount_matches_model(self):
        txn = PaymentTransactionFactory(amount="999.00")
        data = PaymentTransactionSerializer(txn).data
        assert float(data["amount"]) == 999.0

    def test_paid_at_is_null_before_payment(self):
        txn = PaymentTransactionFactory()
        data = PaymentTransactionSerializer(txn).data
        assert data["paid_at"] is None

    def test_activated_at_is_null_before_activation(self):
        txn = PaymentTransactionFactory()
        data = PaymentTransactionSerializer(txn).data
        assert data["activated_at"] is None


@pytest.mark.django_db
class TestSubscriptionSerializer:
    """SubscriptionSerializer exposes is_premium, activated_at, and source."""

    def test_contains_expected_fields(self):
        sub = SubscriptionFactory()
        data = SubscriptionSerializer(sub).data
        assert set(data.keys()) == {"is_premium", "activated_at", "source"}

    def test_is_premium_false_for_free_subscription(self):
        sub = SubscriptionFactory(is_premium=False)
        data = SubscriptionSerializer(sub).data
        assert data["is_premium"] is False

    def test_is_premium_true_after_activation(self):
        sub = SubscriptionFactory()
        sub.activate(source="razorpay")
        data = SubscriptionSerializer(sub).data
        assert data["is_premium"] is True

    def test_source_is_razorpay_after_activation(self):
        sub = SubscriptionFactory()
        sub.activate(source="razorpay")
        data = SubscriptionSerializer(sub).data
        assert data["source"] == "razorpay"

    def test_activated_at_is_null_before_activation(self):
        sub = SubscriptionFactory()
        data = SubscriptionSerializer(sub).data
        assert data["activated_at"] is None


@pytest.mark.django_db
class TestSuperAdminSubscriptionSerializer:
    """SuperAdminSubscriptionSerializer includes denormalised tenant fields."""

    def test_contains_all_expected_fields(self):
        sub = SubscriptionFactory()
        data = SuperAdminSubscriptionSerializer(sub).data
        expected = {
            "id", "tenant_id", "tenant_name", "tenant_is_active",
            "is_premium", "activated_at", "source",
            "payment_transaction_id", "created_at", "updated_at",
        }
        assert expected == set(data.keys())

    def test_tenant_id_matches_subscription_tenant(self):
        sub = SubscriptionFactory()
        data = SuperAdminSubscriptionSerializer(sub).data
        assert str(data["tenant_id"]) == str(sub.tenant.id)

    def test_tenant_name_matches_subscription_tenant(self):
        sub = SubscriptionFactory()
        data = SuperAdminSubscriptionSerializer(sub).data
        assert data["tenant_name"] == sub.tenant.name

    def test_tenant_is_active_reflects_tenant_state(self):
        tenant = TenantFactory(is_active=True)
        sub = SubscriptionFactory(tenant=tenant)
        data = SuperAdminSubscriptionSerializer(sub).data
        assert data["tenant_is_active"] is True

    def test_payment_transaction_id_is_null_when_no_transaction(self):
        sub = SubscriptionFactory()
        data = SuperAdminSubscriptionSerializer(sub).data
        assert data["payment_transaction_id"] is None

    def test_payment_transaction_id_set_after_activation(self):
        tenant = TenantFactory()
        txn = PaymentTransactionFactory(tenant=tenant)
        sub = SubscriptionFactory(tenant=tenant)
        sub.activate(transaction=txn)
        data = SuperAdminSubscriptionSerializer(sub).data
        assert str(data["payment_transaction_id"]) == str(txn.id)


@pytest.mark.django_db
class TestSuperAdminPaymentTransactionSerializer:
    """SuperAdminPaymentTransactionSerializer includes denormalised tenant fields."""

    def test_contains_all_expected_fields(self):
        txn = PaymentTransactionFactory()
        data = SuperAdminPaymentTransactionSerializer(txn).data
        expected = {
            "id", "tenant_id", "tenant_name", "tenant_is_active",
            "razorpay_payment_link_id", "razorpay_order_id",
            "payment_link_url", "razorpay_payment_id",
            "amount", "currency", "status", "attempt_number",
            "error_message", "paid_at", "verified_at", "activated_at",
            "created_at", "updated_at",
        }
        assert expected == set(data.keys())

    def test_tenant_id_matches_transaction_tenant(self):
        txn = PaymentTransactionFactory()
        data = SuperAdminPaymentTransactionSerializer(txn).data
        assert str(data["tenant_id"]) == str(txn.tenant.id)

    def test_tenant_name_matches_transaction_tenant(self):
        txn = PaymentTransactionFactory()
        data = SuperAdminPaymentTransactionSerializer(txn).data
        assert data["tenant_name"] == txn.tenant.name

    def test_status_value_is_created_by_default(self):
        txn = PaymentTransactionFactory()
        data = SuperAdminPaymentTransactionSerializer(txn).data
        assert data["status"] == "CREATED"

    def test_error_message_empty_by_default(self):
        txn = PaymentTransactionFactory()
        data = SuperAdminPaymentTransactionSerializer(txn).data
        assert data["error_message"] == ""
