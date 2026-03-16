"""Tests for payment app models: PaymentTransaction, Subscription, WebhookEvent."""
import pytest
from django.db import IntegrityError
from django.utils import timezone

from common.enums import PaymentStatus
from payments.models import PaymentTransaction
from tests.factories.payment_factory import (
    PaymentTransactionFactory,
    SubscriptionFactory,
    WebhookEventFactory,
)
from tests.factories.tenant_factory import TenantFactory


@pytest.mark.django_db
class TestPaymentTransactionCreation:
    """PaymentTransaction is created with correct defaults."""

    def test_creates_with_required_fields(self):
        txn = PaymentTransactionFactory()
        assert txn.pk is not None

    def test_default_status_is_created(self):
        txn = PaymentTransactionFactory()
        assert txn.status == PaymentStatus.CREATED

    def test_default_currency_is_inr(self):
        txn = PaymentTransactionFactory()
        assert txn.currency == "INR"

    def test_default_attempt_number_is_one(self):
        txn = PaymentTransactionFactory()
        assert txn.attempt_number == 1

    def test_created_at_is_set_automatically(self):
        txn = PaymentTransactionFactory()
        assert txn.created_at is not None

    def test_str_contains_tenant_name_and_status(self):
        txn = PaymentTransactionFactory()
        result = str(txn)
        assert txn.tenant.name in result
        assert txn.status in result


@pytest.mark.django_db
class TestPaymentTransactionUniqueness:
    """razorpay_payment_link_id must be unique across transactions."""

    def test_duplicate_payment_link_id_raises_integrity_error(self):
        txn = PaymentTransactionFactory()
        with pytest.raises(IntegrityError):
            PaymentTransactionFactory(
                tenant=txn.tenant,
                razorpay_payment_link_id=txn.razorpay_payment_link_id,
            )


@pytest.mark.django_db
class TestPaymentTransactionStateMachine:
    """State-transition methods move status and set timestamps correctly."""

    def test_mark_paid_sets_status_and_payment_id(self):
        txn = PaymentTransactionFactory()
        txn.mark_paid("pay_abc123")
        txn.refresh_from_db()
        assert txn.status == PaymentStatus.PAID
        assert txn.razorpay_payment_id == "pay_abc123"
        assert txn.paid_at is not None

    def test_mark_verified_sets_status_and_signature(self):
        txn = PaymentTransactionFactory(status=PaymentStatus.PAID)
        txn.mark_verified("sig_xyz")
        txn.refresh_from_db()
        assert txn.status == PaymentStatus.VERIFIED
        assert txn.razorpay_signature == "sig_xyz"
        assert txn.verified_at is not None

    def test_mark_activated_sets_status_and_activated_at(self):
        txn = PaymentTransactionFactory(status=PaymentStatus.VERIFIED)
        txn.mark_activated()
        txn.refresh_from_db()
        assert txn.status == PaymentStatus.ACTIVATED
        assert txn.activated_at is not None

    def test_mark_failed_sets_status_and_error_message(self):
        txn = PaymentTransactionFactory()
        txn.mark_failed("card declined")
        txn.refresh_from_db()
        assert txn.status == PaymentStatus.FAILED
        assert "card declined" in txn.error_message

    def test_mark_paid_persists_to_database(self):
        txn = PaymentTransactionFactory()
        txn.mark_paid("pay_persist")
        fresh = PaymentTransaction.objects.get(pk=txn.pk)
        assert fresh.razorpay_payment_id == "pay_persist"

    def test_mark_activated_persists_activated_at(self):
        txn = PaymentTransactionFactory()
        before = timezone.now()
        txn.mark_activated()
        txn.refresh_from_db()
        assert txn.activated_at >= before


@pytest.mark.django_db
class TestSubscriptionCreation:
    """Subscription defaults and OneToOne constraint."""

    def test_creates_with_defaults(self):
        sub = SubscriptionFactory()
        assert sub.pk is not None
        assert sub.is_premium is False

    def test_str_shows_free_for_non_premium(self):
        sub = SubscriptionFactory(is_premium=False)
        assert "Free" in str(sub)

    def test_str_shows_premium_for_premium(self):
        sub = SubscriptionFactory(is_premium=True)
        assert "Premium" in str(sub)

    def test_one_tenant_cannot_have_two_subscriptions(self):
        tenant = TenantFactory()
        SubscriptionFactory(tenant=tenant)
        with pytest.raises(IntegrityError):
            SubscriptionFactory(tenant=tenant)


@pytest.mark.django_db
class TestSubscriptionActivate:
    """Subscription.activate() upgrades status and links transaction."""

    def test_activate_sets_is_premium_true(self):
        sub = SubscriptionFactory()
        sub.activate()
        sub.refresh_from_db()
        assert sub.is_premium is True

    def test_activate_records_source(self):
        sub = SubscriptionFactory()
        sub.activate(source="razorpay")
        sub.refresh_from_db()
        assert sub.source == "razorpay"

    def test_activate_sets_activated_at(self):
        sub = SubscriptionFactory()
        before = timezone.now()
        sub.activate()
        sub.refresh_from_db()
        assert sub.activated_at >= before

    def test_activate_links_payment_transaction(self):
        tenant = TenantFactory()
        txn = PaymentTransactionFactory(tenant=tenant)
        sub = SubscriptionFactory(tenant=tenant)
        sub.activate(transaction=txn)
        sub.refresh_from_db()
        assert sub.payment_transaction == txn


@pytest.mark.django_db
class TestWebhookEventCreation:
    """WebhookEvent stores event data and has correct defaults."""

    def test_creates_with_required_fields(self):
        event = WebhookEventFactory()
        assert event.pk is not None

    def test_default_processed_is_false(self):
        event = WebhookEventFactory()
        assert event.processed is False

    def test_str_contains_event_type_and_id(self):
        event = WebhookEventFactory(event_type="payment.captured", razorpay_event_id="evt_test")
        result = str(event)
        assert "payment.captured" in result
        assert "evt_test" in result


@pytest.mark.django_db
class TestWebhookEventUniqueness:
    """razorpay_event_id and idempotency_key must each be unique."""

    def test_duplicate_event_id_raises_integrity_error(self):
        event = WebhookEventFactory()
        with pytest.raises(IntegrityError):
            WebhookEventFactory(
                razorpay_event_id=event.razorpay_event_id,
            )

    def test_duplicate_idempotency_key_raises_integrity_error(self):
        event = WebhookEventFactory()
        with pytest.raises(IntegrityError):
            WebhookEventFactory(idempotency_key=event.idempotency_key)


@pytest.mark.django_db
class TestWebhookEventStateMachine:
    """mark_processed and mark_failed update the event correctly."""

    def test_mark_processed_sets_processed_true(self):
        event = WebhookEventFactory()
        event.mark_processed()
        event.refresh_from_db()
        assert event.processed is True
        assert event.processed_at is not None

    def test_mark_failed_stores_error_message(self):
        event = WebhookEventFactory()
        event.mark_failed("something went wrong")
        event.refresh_from_db()
        assert "something went wrong" in event.error_message

    def test_mark_processed_sets_processed_at_timestamp(self):
        event = WebhookEventFactory()
        before = timezone.now()
        event.mark_processed()
        event.refresh_from_db()
        assert event.processed_at >= before
