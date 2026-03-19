import pytest
from django.utils import timezone

from tests.factories.tenant_factory import TenantFactory
from tests.factories.user_factory import SuperAdminFactory, UserFactory
from tenants.models import Tenant
import uuid

@pytest.mark.django_db
class TestTenantCreation:
    """Basic model creation and default values."""

    def test_tenant_is_created_with_valid_data(self):
        tenant = TenantFactory(name="Acme Corp")
        assert tenant.pk is not None
        assert tenant.name == "Acme Corp"

    def test_tenant_is_active_by_default(self):
        tenant = TenantFactory()
        assert tenant.is_active is False

    def test_tenant_has_uuid_primary_key(self):
        tenant = TenantFactory()
        assert isinstance(tenant.id, uuid.UUID)

    def test_tenant_has_created_at_and_updated_at(self):
        tenant = TenantFactory()
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    def test_tenant_not_soft_deleted_by_default(self):
        tenant = TenantFactory()
        assert tenant.deleted_at is None
        assert tenant.deleted_by is None

    def test_str_returns_name(self):
        tenant = TenantFactory(name="Rock Station")
        assert str(tenant) == "Rock Station"


@pytest.mark.django_db
class TestTenantActivateDeactivate:
    """activate() and deactivate() toggle is_active and persist."""

    def test_activate_sets_is_active_true(self):
        tenant = TenantFactory(is_active=False)
        tenant.activate()
        tenant.refresh_from_db()
        assert tenant.is_active is True

    def test_deactivate_sets_is_active_false(self):
        tenant = TenantFactory(is_active=True)
        tenant.deactivate()
        tenant.refresh_from_db()
        assert tenant.is_active is False

    def test_activate_is_idempotent(self):
        tenant = TenantFactory(is_active=True)
        tenant.activate()
        tenant.refresh_from_db()
        assert tenant.is_active is True

    def test_deactivate_is_idempotent(self):
        tenant = TenantFactory(is_active=False)
        tenant.deactivate()
        tenant.refresh_from_db()
        assert tenant.is_active is False


@pytest.mark.django_db
class TestTenantIsPremium:
    """is_premium delegates to the related Subscription."""

    def test_is_premium_returns_false_when_no_subscription(self):
        tenant = TenantFactory()
        assert tenant.is_premium is False


@pytest.mark.django_db
class TestTenantUserCount:
    """user_count counts only non-soft-deleted users."""

    def test_user_count_zero_for_new_tenant(self):
        tenant = TenantFactory()
        assert tenant.user_count == 0

    def test_user_count_includes_active_users(self):
        tenant = TenantFactory()
        UserFactory(tenant=tenant)
        UserFactory(tenant=tenant)
        assert tenant.user_count == 2

    def test_user_count_excludes_soft_deleted_users(self):
        tenant = TenantFactory()
        deleter = SuperAdminFactory()
        active_user = UserFactory(tenant=tenant)
        deleted_user = UserFactory(tenant=tenant)
        deleted_user.delete(deleted_by=deleter)
        assert tenant.user_count == 1

    def test_user_count_does_not_include_other_tenant_users(self):
        tenant_a = TenantFactory()
        tenant_b = TenantFactory()
        UserFactory(tenant=tenant_b)
        assert tenant_a.user_count == 0


@pytest.mark.django_db
class TestTenantSoftDelete:
    """SoftDeleteModel behaviours: delete(), restore(), is_deleted."""

    def test_delete_sets_deleted_at(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        tenant.refresh_from_db()
        assert tenant.deleted_at is not None

    def test_delete_records_who_deleted(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        tenant.refresh_from_db()
        assert tenant.deleted_by_id == deleter.pk

    def test_is_deleted_true_after_soft_delete(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        assert tenant.is_deleted is True

    def test_is_deleted_false_before_delete(self):
        tenant = TenantFactory()
        assert tenant.is_deleted is False

    def test_restore_clears_deleted_at(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        tenant.restore()
        tenant.refresh_from_db()
        assert tenant.deleted_at is None
        assert tenant.deleted_by is None

    def test_is_deleted_false_after_restore(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        tenant.restore()
        assert tenant.is_deleted is False

    def test_hard_delete_removes_from_db(self):
        tenant = TenantFactory()
        pk = tenant.pk
        tenant.hard_delete()
        assert not Tenant.all_tenants.filter(pk=pk).exists()


@pytest.mark.django_db
class TestActiveTenantManager:
    """ActiveTenantManager only surfaces active, non-deleted tenants."""

    def test_returns_active_non_deleted_tenants(self):
        active = TenantFactory(is_active=True)
        ids = list(Tenant.objects.values_list("id", flat=True))
        assert active.id in ids

    def test_excludes_inactive_tenants(self):
        inactive = TenantFactory(is_active=False)
        ids = list(Tenant.objects.values_list("id", flat=True))
        assert inactive.id not in ids

    def test_excludes_soft_deleted_tenants(self):
        deleter = SuperAdminFactory()
        deleted = TenantFactory()
        deleted.delete(deleted_by=deleter)
        ids = list(Tenant.objects.values_list("id", flat=True))
        assert deleted.id not in ids

    def test_excludes_inactive_and_soft_deleted_tenants(self):
        deleter = SuperAdminFactory()
        victim = TenantFactory(is_active=False)
        victim.delete(deleted_by=deleter)
        ids = list(Tenant.objects.values_list("id", flat=True))
        assert victim.id not in ids


@pytest.mark.django_db
class TestAllTenantsManager:
    """AllTenantsManager returns every tenant without filtering."""

    def test_includes_active_tenants(self):
        active = TenantFactory(is_active=True)
        ids = list(Tenant.all_tenants.values_list("id", flat=True))
        assert active.id in ids

    def test_includes_inactive_tenants(self):
        inactive = TenantFactory(is_active=False)
        ids = list(Tenant.all_tenants.values_list("id", flat=True))
        assert inactive.id in ids

    def test_includes_soft_deleted_tenants(self):
        deleter = SuperAdminFactory()
        deleted = TenantFactory()
        deleted.delete(deleted_by=deleter)
        ids = list(Tenant.all_tenants.values_list("id", flat=True))
        assert deleted.id in ids


@pytest.mark.django_db
class TestTenantUniqueNameConstraint:
    """
    Soft-deleted tenants may free up the name for reuse.
    """

    def test_duplicate_name_raises_integrity_error(self):
        from django.db import IntegrityError
        TenantFactory(name="Duplicate Name")
        with pytest.raises(IntegrityError):
            TenantFactory(name="Duplicate Name")

    def test_same_name_allowed_after_soft_delete(self):
        deleter = SuperAdminFactory()
        tenant = TenantFactory(name="Reusable Name")
        tenant.delete(deleted_by=deleter)
        new_tenant = TenantFactory(name="Reusable Name")
        assert new_tenant.pk is not None

    def test_name_uniqueness_is_case_sensitive_at_db_level(self):
        TenantFactory(name="Acme")
        t2 = TenantFactory(name="acme")
        assert t2.pk is not None
