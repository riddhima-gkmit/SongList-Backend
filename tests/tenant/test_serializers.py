import pytest

from tests.factories.tenant_factory import TenantFactory
from tests.factories.user_factory import SuperAdminFactory, UserFactory
from tenants.serializers import TenantSerializer
from tenants.models import Tenant

import uuid

@pytest.mark.django_db
class TestTenantSerializerSerialization:
    """Output shape and field correctness."""

    def test_serializes_expected_fields(self):
        tenant = TenantFactory(name="Jazz Hub", is_active=True)
        data = TenantSerializer(tenant).data
        assert set(data.keys()) == {
            "id", "name", "is_active", "is_premium", "user_count",
            "created_at", "updated_at",
        }

    def test_serializes_name_correctly(self):
        tenant = TenantFactory(name="Rock Radio")
        data = TenantSerializer(tenant).data
        assert data["name"] == "Rock Radio"

    def test_serializes_is_active_correctly(self):
        active = TenantFactory(is_active=True)
        inactive = TenantFactory(is_active=False)
        assert TenantSerializer(active).data["is_active"] is True
        assert TenantSerializer(inactive).data["is_active"] is False

    def test_id_is_present_and_is_string(self):
        tenant = TenantFactory()
        data = TenantSerializer(tenant).data
        assert "id" in data
        # UUIDs are serialized as strings
        assert isinstance(data["id"], str)

    def test_created_at_and_updated_at_are_present(self):
        tenant = TenantFactory()
        data = TenantSerializer(tenant).data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None


@pytest.mark.django_db
class TestTenantSerializerReadOnlyFields:
    """id and created_at must never be writable."""

    def test_id_is_read_only(self):
        tenant = TenantFactory()
        fake_id = str(uuid.uuid4())
        serializer = TenantSerializer(
            tenant, data={"id": fake_id, "name": tenant.name}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert str(instance.id) != fake_id

    def test_created_at_is_read_only(self):
        tenant = TenantFactory()
        serializer = TenantSerializer(
            tenant,
            data={"created_at": "2000-01-01T00:00:00Z", "name": tenant.name},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert str(instance.created_at) != "2000-01-01 00:00:00+00:00"


@pytest.mark.django_db
class TestTenantSerializerRequiredFields:
    """name is the only required writable field."""

    def test_missing_name_is_invalid(self):
        serializer = TenantSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_blank_name_is_invalid(self):
        serializer = TenantSerializer(data={"name": ""})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_name_only_is_valid(self):
        serializer = TenantSerializer(data={"name": "Brand New Tenant"})
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestTenantSerializerValidateName:
    """validate_name enforces case-insensitive uniqueness and whitespace trimming."""

    def test_duplicate_name_raises_validation_error(self):
        TenantFactory(name="Music World")
        serializer = TenantSerializer(data={"name": "Music World"})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_duplicate_name_case_insensitive_raises_error(self):
        TenantFactory(name="Music World")
        for variant in ("music world", "MUSIC WORLD", "Music world", "mUsIc WoRlD"):
            serializer = TenantSerializer(data={"name": variant})
            assert not serializer.is_valid(), f"Expected invalid for: {variant!r}"
            assert "name" in serializer.errors

    def test_name_with_leading_trailing_whitespace_is_stripped(self):
        serializer = TenantSerializer(data={"name": "  Stripped Name  "})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "Stripped Name"

    def test_whitespace_stripped_name_still_checked_for_uniqueness(self):
        TenantFactory(name="Padded Tenant")
        serializer = TenantSerializer(data={"name": "  Padded Tenant  "})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_reuse_of_soft_deleted_tenant_name_is_allowed(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory(name="Gone Tenant")
        tenant.delete(deleted_by=deleter)
        serializer = TenantSerializer(data={"name": "Gone Tenant"})
        assert serializer.is_valid(), serializer.errors

    def test_reuse_of_soft_deleted_name_case_insensitive(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory(name="Gone Tenant")
        tenant.delete(deleted_by=deleter)
        serializer = TenantSerializer(data={"name": "gone tenant"})
        assert serializer.is_valid(), serializer.errors

    def test_update_with_same_name_excludes_current_instance(self):
        tenant = TenantFactory(name="Unchanged Name")
        serializer = TenantSerializer(tenant, data={"name": "Unchanged Name"}, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_update_with_another_tenants_name_raises_error(self):
        tenant_a = TenantFactory(name="Tenant A")
        TenantFactory(name="Tenant B")
        serializer = TenantSerializer(tenant_a, data={"name": "Tenant B"}, partial=True)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_unique_name_is_accepted(self):
        serializer = TenantSerializer(data={"name": "Completely Unique Tenant"})
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestTenantSerializerMethodFields:
    """get_user_count and get_is_premium read from model properties."""

    def test_user_count_is_zero_for_new_tenant(self):
        tenant = TenantFactory()
        data = TenantSerializer(tenant).data
        assert data["user_count"] == 0

    def test_user_count_reflects_active_users(self):
        tenant = TenantFactory()
        UserFactory(tenant=tenant)
        UserFactory(tenant=tenant)
        data = TenantSerializer(tenant).data
        assert data["user_count"] == 2

    def test_user_count_excludes_deleted_users(self):
        tenant = TenantFactory()
        deleter = SuperAdminFactory()
        UserFactory(tenant=tenant)
        deleted = UserFactory(tenant=tenant)
        deleted.delete(deleted_by=deleter)
        data = TenantSerializer(tenant).data
        assert data["user_count"] == 1

    def test_is_premium_false_when_no_subscription(self):
        tenant = TenantFactory()
        data = TenantSerializer(tenant).data
        assert data["is_premium"] is False


@pytest.mark.django_db
class TestTenantSerializerCreate:
    """serializer.save() correctly persists a new Tenant."""

    def test_save_creates_tenant_in_db(self):
        serializer = TenantSerializer(data={"name": "Persist Me"})
        assert serializer.is_valid(), serializer.errors
        tenant = serializer.save()
        assert Tenant.all_tenants.filter(pk=tenant.pk).exists()

    def test_save_sets_is_active_true_by_default(self):
        serializer = TenantSerializer(data={"name": "Default Active"})
        assert serializer.is_valid(), serializer.errors
        tenant = serializer.save()
        assert tenant.is_active is True

    def test_save_with_is_active_false(self):
        serializer = TenantSerializer(data={"name": "Inactive Tenant", "is_active": False})
        assert serializer.is_valid(), serializer.errors
        tenant = serializer.save()
        assert tenant.is_active is False


@pytest.mark.django_db
class TestTenantSerializerUpdate:
    """Partial updates via the serializer."""

    def test_partial_update_name(self):
        tenant = TenantFactory(name="Old Name")
        serializer = TenantSerializer(tenant, data={"name": "New Name"}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.name == "New Name"

    def test_partial_update_is_active(self):
        tenant = TenantFactory(is_active=True)
        serializer = TenantSerializer(tenant, data={"is_active": False}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.is_active is False
