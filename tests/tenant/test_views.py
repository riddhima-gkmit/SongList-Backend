import uuid

import pytest
from rest_framework import status
from tests.conftest import _make_jwt_client

from tenants.models import Tenant
from tests.factories.tenant_factory import TenantFactory
from tests.factories.user_factory import (
    AdminUserFactory,
    SuperAdminFactory,
    UserFactory,
)

LIST_URL = "/api/v1/tenants/"


def detail_url(tenant_id):
    return f"/api/v1/tenants/{tenant_id}/"


def activate_url(tenant_id):
    return f"/api/v1/tenants/{tenant_id}/activate/"


def deactivate_url(tenant_id):
    return f"/api/v1/tenants/{tenant_id}/deactivate/"


NONEXISTENT_UUID = str(uuid.uuid4())

@pytest.mark.django_db
class TestTenantListGet:

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listener_returns_403(self, listener_client):
        response = listener_client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_returns_403(self, admin_client):
        response = admin_client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_returns_200(self, super_admin_client, db):
        response = super_admin_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_response_is_paginated(self, super_admin_client, db):
        TenantFactory.create_batch(3)
        response = super_admin_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "count" in body
        assert "page" in body
        assert "data" in body

    def test_response_includes_all_tenants_including_inactive(self, super_admin_client, db):
        active = TenantFactory(is_active=True)
        inactive = TenantFactory(is_active=False)
        response = super_admin_client.get(LIST_URL)
        ids = [item["id"] for item in response.json()["data"]]
        assert str(active.id) in ids
        assert str(inactive.id) in ids

    def test_response_includes_soft_deleted_tenants(self, super_admin_client, db):
        """The list view uses all_tenants manager so soft-deleted records appear."""
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.get(LIST_URL)
        ids = [item["id"] for item in response.json()["data"]]
        assert str(tenant.id) in ids

    def test_tenant_data_shape(self, super_admin_client, db):
        TenantFactory(name="Shape Test")
        response = super_admin_client.get(LIST_URL)
        first = response.json()["data"][0]
        assert set(first.keys()) >= {"id", "name", "is_active", "is_premium", "user_count"}

@pytest.mark.django_db
class TestTenantCreate:

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(LIST_URL, {"name": "New Tenant"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_returns_403(self, admin_client):
        response = admin_client.post(LIST_URL, {"name": "New Tenant"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listener_returns_403(self, listener_client):
        response = listener_client.post(LIST_URL, {"name": "New Tenant"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_creates_tenant_returns_201(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": "Created Tenant"})
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_response_has_success_status(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": "Success Tenant"})
        assert response.json()["status"] == "success"

    def test_create_response_contains_tenant_data(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": "Data Tenant"})
        data = response.json()["data"]
        assert data["name"] == "Data Tenant"
        assert "id" in data

    def test_created_tenant_is_active_by_default(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": "Active By Default"}, format="json")
        assert response.json()["data"]["is_active"] is True

    def test_created_tenant_persisted_in_db(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": "Persisted Tenant"})
        tenant_id = response.json()["data"]["id"]
        assert Tenant.all_tenants.filter(id=tenant_id).exists()

    def test_missing_name_returns_400(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_name_returns_400(self, super_admin_client):
        response = super_admin_client.post(LIST_URL, {"name": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_name_returns_400(self, super_admin_client, db):
        TenantFactory(name="Existing Tenant")
        response = super_admin_client.post(LIST_URL, {"name": "Existing Tenant"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_name_case_insensitive_returns_400(self, super_admin_client, db):
        TenantFactory(name="Case Clash")
        response = super_admin_client.post(LIST_URL, {"name": "case clash"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_name_of_soft_deleted_tenant_allowed(self, super_admin_client, db):
        deleter = SuperAdminFactory()
        tenant = TenantFactory(name="Recycled Name")
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.post(LIST_URL, {"name": "Recycled Name"})
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestTenantDetailGet:

    def test_unauthenticated_returns_401(self, api_client, tenant):
        response = api_client.get(detail_url(tenant.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listener_returns_403(self, listener_client, tenant):
        response = listener_client.get(detail_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_retrieves_tenant(self, super_admin_client, tenant):
        response = super_admin_client.get(detail_url(tenant.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == str(tenant.id)

    def test_admin_retrieves_own_tenant(self, admin_client, tenant):
        response = admin_client.get(detail_url(tenant.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == str(tenant.id)

    def test_super_admin_nonexistent_uuid_returns_404(self, super_admin_client):
        response = super_admin_client.get(detail_url(NONEXISTENT_UUID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_super_admin_soft_deleted_tenant_returns_404(self, super_admin_client, db):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.get(detail_url(tenant.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_inactive_tenant_returns_404(self, db):
        inactive_tenant = TenantFactory(is_active=False)
        admin = AdminUserFactory(tenant=inactive_tenant)
        client = _make_jwt_client(admin)
        response = client.get(detail_url(inactive_tenant.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_has_success_status(self, super_admin_client, tenant):
        response = super_admin_client.get(detail_url(tenant.id))
        assert response.json()["status"] == "success"


@pytest.mark.django_db
class TestTenantDetailPatch:

    def test_unauthenticated_returns_401(self, api_client, tenant):
        response = api_client.patch(detail_url(tenant.id), {"name": "X"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_returns_403(self, admin_client, tenant):
        response = admin_client.patch(detail_url(tenant.id), {"name": "X"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listener_returns_403(self, listener_client, tenant):
        response = listener_client.patch(detail_url(tenant.id), {"name": "X"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_updates_name(self, super_admin_client, tenant):
        response = super_admin_client.patch(
            detail_url(tenant.id), {"name": "Updated Name"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["name"] == "Updated Name"

    def test_super_admin_updates_is_active(self, super_admin_client, tenant):
        response = super_admin_client.patch(
            detail_url(tenant.id), {"is_active": False}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["is_active"] is False

    def test_nonexistent_uuid_returns_404(self, super_admin_client):
        response = super_admin_client.patch(
            detail_url(NONEXISTENT_UUID), {"name": "X"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_duplicate_name_returns_400(self, super_admin_client, db):
        TenantFactory(name="Conflict Name")
        own_tenant = TenantFactory(name="My Tenant")
        response = super_admin_client.patch(
            detail_url(own_tenant.id), {"name": "Conflict Name"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_persisted_in_db(self, super_admin_client, tenant):
        super_admin_client.patch(
            detail_url(tenant.id), {"name": "Persisted Update"}, format="json"
        )
        tenant.refresh_from_db()
        assert tenant.name == "Persisted Update"


@pytest.mark.django_db
class TestTenantDetailDelete:

    def test_unauthenticated_returns_401(self, api_client, tenant):
        response = api_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_returns_403(self, admin_client, tenant):
        response = admin_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listener_returns_403(self, listener_client, tenant):
        response = listener_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_deletes_empty_tenant_returns_204(self, super_admin_client, tenant):
        response = super_admin_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_deletion_soft_deletes_tenant(self, super_admin_client, tenant):
        super_admin_client.delete(detail_url(tenant.id))
        tenant.refresh_from_db()
        assert tenant.is_deleted is True

    def test_delete_with_active_users_returns_400(self, super_admin_client, tenant, db):
        UserFactory(tenant=tenant)
        response = super_admin_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_with_active_users_error_message(self, super_admin_client, tenant, db):
        UserFactory(tenant=tenant)
        response = super_admin_client.delete(detail_url(tenant.id))
        body = response.json()
        assert body["status"] == "error"
        assert "active user" in body["message"].lower()

    def test_delete_not_blocked_by_soft_deleted_users(self, super_admin_client, tenant, db):
        deleter = SuperAdminFactory()
        user = UserFactory(tenant=tenant)
        user.delete(deleted_by=deleter)
        response = super_admin_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_nonexistent_uuid_returns_404(self, super_admin_client):
        response = super_admin_client.delete(detail_url(NONEXISTENT_UUID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_already_soft_deleted_returns_404(self, super_admin_client, db):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.delete(detail_url(tenant.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTenantActivate:

    def test_unauthenticated_returns_401(self, api_client, tenant):
        response = api_client.patch(activate_url(tenant.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_returns_403(self, admin_client, tenant):
        response = admin_client.patch(activate_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listener_returns_403(self, listener_client, tenant):
        response = listener_client.patch(activate_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_activates_inactive_tenant(self, super_admin_client, db):
        inactive = TenantFactory(is_active=False)
        response = super_admin_client.patch(activate_url(inactive.id))
        assert response.status_code == status.HTTP_200_OK

    def test_activation_persisted_in_db(self, super_admin_client, db):
        inactive = TenantFactory(is_active=False)
        super_admin_client.patch(activate_url(inactive.id))
        inactive.refresh_from_db()
        assert inactive.is_active is True

    def test_response_has_success_status(self, super_admin_client, db):
        inactive = TenantFactory(is_active=False)
        response = super_admin_client.patch(activate_url(inactive.id))
        assert response.json()["status"] == "success"

    def test_nonexistent_uuid_returns_404(self, super_admin_client):
        response = super_admin_client.patch(activate_url(NONEXISTENT_UUID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_tenant_returns_404(self, super_admin_client, db):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.patch(activate_url(tenant.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activating_already_active_tenant_is_ok(self, super_admin_client, tenant):
        response = super_admin_client.patch(activate_url(tenant.id))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTenantDeactivate:

    def test_unauthenticated_returns_401(self, api_client, tenant):
        response = api_client.patch(deactivate_url(tenant.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_returns_403(self, admin_client, tenant):
        response = admin_client.patch(deactivate_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listener_returns_403(self, listener_client, tenant):
        response = listener_client.patch(deactivate_url(tenant.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_deactivates_active_tenant(self, super_admin_client, tenant):
        response = super_admin_client.patch(deactivate_url(tenant.id))
        assert response.status_code == status.HTTP_200_OK

    def test_deactivation_persisted_in_db(self, super_admin_client, tenant):
        super_admin_client.patch(deactivate_url(tenant.id))
        tenant.refresh_from_db()
        assert tenant.is_active is False

    def test_response_has_success_status(self, super_admin_client, tenant):
        response = super_admin_client.patch(deactivate_url(tenant.id))
        assert response.json()["status"] == "success"

    def test_nonexistent_uuid_returns_404(self, super_admin_client):
        response = super_admin_client.patch(deactivate_url(NONEXISTENT_UUID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_tenant_returns_404(self, super_admin_client, db):
        deleter = SuperAdminFactory()
        tenant = TenantFactory()
        tenant.delete(deleted_by=deleter)
        response = super_admin_client.patch(deactivate_url(tenant.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivating_already_inactive_tenant_is_ok(self, super_admin_client, db):
        inactive = TenantFactory(is_active=False)
        response = super_admin_client.patch(deactivate_url(inactive.id))
        assert response.status_code == status.HTTP_200_OK
