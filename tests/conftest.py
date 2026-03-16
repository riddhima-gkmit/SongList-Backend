import pytest
from unittest.mock import MagicMock, patch

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken


@pytest.fixture(autouse=True)
def use_locmem_cache(settings):
    """Replace the Redis cache with a per-process in-memory cache."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


def _make_jwt_client(user):
    """Return an APIClient carrying a valid JWT access token for *user*."""
    client = APIClient()
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def tenant(db):
    """Return a default active, non-deleted Tenant."""
    from tests.factories.tenant_factory import TenantFactory
    return TenantFactory()


@pytest.fixture
def super_admin(db):
    """Return a SUPER_ADMIN user (no tenant)."""
    from tests.factories.user_factory import SuperAdminFactory
    return SuperAdminFactory()


@pytest.fixture
def admin_user(db, tenant):
    """Return an ADMIN user belonging to the shared *tenant* fixture."""
    from tests.factories.user_factory import AdminUserFactory
    return AdminUserFactory(tenant=tenant)


@pytest.fixture
def listener_user(db, tenant):
    """Return a LISTENER user belonging to the shared *tenant* fixture."""
    from tests.factories.user_factory import UserFactory
    return UserFactory(tenant=tenant)


@pytest.fixture
def super_admin_client(super_admin):
    """Return an APIClient authenticated as SUPER_ADMIN."""
    return _make_jwt_client(super_admin)


@pytest.fixture
def admin_client(admin_user):
    """Return an APIClient authenticated as ADMIN."""
    return _make_jwt_client(admin_user)


@pytest.fixture
def listener_client(listener_user):
    """Return an APIClient authenticated as LISTENER."""
    return _make_jwt_client(listener_user)


@pytest.fixture(autouse=True)
def razorpay_creds(settings):
    """Inject dummy Razorpay credentials so the SDK never hits production."""
    settings.RAZORPAY_KEY_ID = "test_key_id"
    settings.RAZORPAY_KEY_SECRET = "test_key_secret"
    settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"


@pytest.fixture
def mock_razorpay_client():
    """Mock the low-level razorpay.Client so no real API calls are made."""
    with patch("payments.services.razorpay.Client") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_razorpay_service():
    """Mock the entire RazorpayService class for view-layer isolation."""
    with patch("payments.views.RazorpayService") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance
