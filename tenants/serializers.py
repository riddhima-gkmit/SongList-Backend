from rest_framework import serializers
from tenants.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for tenant CRUD operations."""

    user_count = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "is_active",
            "is_premium",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user_count(self, obj):
        """Get the user count from the model property."""
        return obj.user_count

    def get_is_premium(self, obj):
        """Get the premium status from the model property."""
        return obj.is_premium

    def validate_name(self, value):
        """
        Ensure name is unique (case-insensitive).
        Allow reuse of name if existing tenant is soft-deleted.
        Block if existing tenant is active or deactivated (not soft-deleted).
        """
        value = value.strip()
        
        # Check for existing tenants with same name (case-insensitive)
        # Use all_tenants to check all tenants including inactive ones
        qs = Tenant.all_tenants.filter(name__iexact=value)
        
        # Exclude current instance if updating
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        # Check if any non-soft-deleted tenant exists with this name
        # (either active or deactivated, but not soft-deleted)
        existing_active = qs.filter(deleted_at__isnull=True)
        
        if existing_active.exists():
            raise serializers.ValidationError(
                "Tenant with this name already exists. Please choose a different name."
            )
        
        # If only soft-deleted tenants exist, allow reuse of the name
        return value
