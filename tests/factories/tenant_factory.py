import factory

from tenants.models import Tenant


class TenantFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Test Tenant {n}")
    is_active = True
