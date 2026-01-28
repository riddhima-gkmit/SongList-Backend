from rest_framework import serializers
from users.models import User


class DeletedUserSerializer(serializers.ModelSerializer):
    """Serializer for deleted users. Includes tenant info for SUPER_ADMIN deleted-admin list."""
    deleted_by_username = serializers.CharField(source='deleted_by.username', read_only=True, allow_null=True)
    deletion_type = serializers.SerializerMethodField()
    tenant_id = serializers.UUIDField(source='tenant.id', read_only=True, allow_null=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'role', 'deleted_at',
            'deleted_by', 'deleted_by_username', 'deletion_type',
            'tenant_id', 'tenant_name',
        ]

    def get_deletion_type(self, obj):
        if obj.deleted_by and obj.deleted_by.id == obj.id:
            return 'self'
        return 'admin'
