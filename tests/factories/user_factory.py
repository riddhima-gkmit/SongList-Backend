import factory
from django.contrib.auth import get_user_model

from common.enums import UserRole
from tests.factories.tenant_factory import TenantFactory

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = "Test"
    last_name = "User"
    role = UserRole.LISTENER
    tenant = factory.SubFactory(TenantFactory)
    is_verified = True
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")


class SuperAdminFactory(UserFactory):
    role = UserRole.SUPER_ADMIN
    tenant = None
    username = factory.Sequence(lambda n: f"superadmin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class AdminUserFactory(UserFactory):
    role = UserRole.ADMIN
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
