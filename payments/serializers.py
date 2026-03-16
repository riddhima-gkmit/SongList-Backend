"""
Payment serializers.
"""
from rest_framework import serializers
from payments.models import PaymentTransaction, Subscription




class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for payment transaction."""
    
    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "razorpay_payment_link_id",
            "payment_link_url",
            "razorpay_payment_id",
            "amount",
            "currency",
            "status",
            "created_at",
            "paid_at",
            "activated_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscription status."""
    
    class Meta:
        model = Subscription
        fields = ["is_premium", "activated_at", "source"]


class SuperAdminSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Super Admin to view all subscriptions."""
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_is_active = serializers.BooleanField(source="tenant.is_active", read_only=True)
    payment_transaction_id = serializers.UUIDField(source="payment_transaction.id", read_only=True, allow_null=True)
    
    class Meta:
        model = Subscription
        fields = [
            "id",
            "tenant_id",
            "tenant_name",
            "tenant_is_active",
            "is_premium",
            "activated_at",
            "source",
            "payment_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SuperAdminPaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Super Admin to view all payment transactions."""
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_is_active = serializers.BooleanField(source="tenant.is_active", read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "tenant_id",
            "tenant_name",
            "tenant_is_active",
            "razorpay_payment_link_id",
            "razorpay_order_id",
            "payment_link_url",
            "razorpay_payment_id",
            "amount",
            "currency",
            "status",
            "attempt_number",
            "error_message",
            "paid_at",
            "verified_at",
            "activated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
