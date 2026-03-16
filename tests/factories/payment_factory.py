import factory
from factory.django import DjangoModelFactory

from common.enums import PaymentStatus
from payments.models import PaymentTransaction, Subscription, WebhookEvent
from tests.factories.tenant_factory import TenantFactory


class PaymentTransactionFactory(DjangoModelFactory):

    class Meta:
        model = PaymentTransaction

    tenant = factory.SubFactory(TenantFactory)
    razorpay_payment_link_id = factory.Sequence(lambda n: f"plink_{n:08d}")
    payment_link_url = factory.Sequence(lambda n: f"https://rzp.io/l/test{n}")
    amount = 999.00
    currency = "INR"
    status = PaymentStatus.CREATED
    attempt_number = 1
    metadata = factory.LazyAttribute(lambda o: {"reference_id": f"premium_{o.razorpay_payment_link_id}"})


class SubscriptionFactory(DjangoModelFactory):
    
    class Meta:
        model = Subscription

    tenant = factory.SubFactory(TenantFactory)
    is_premium = False
    source = ""


class WebhookEventFactory(DjangoModelFactory):

    class Meta:
        model = WebhookEvent

    razorpay_event_id = factory.Sequence(lambda n: f"evt_{n:08d}")
    event_type = "payment.captured"
    payload = factory.LazyAttribute(lambda o: {"event": o.event_type})
    signature = "test_signature"
    signature_verified = True
    idempotency_key = factory.Sequence(lambda n: f"idem_{n:08d}")
