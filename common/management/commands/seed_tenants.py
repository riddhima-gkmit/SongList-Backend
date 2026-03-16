from django.core.management.base import BaseCommand
from django.db import transaction
from tenants.models import Tenant


class Command(BaseCommand):
    help = 'Seeds the database with 3-4 tenants'

    @transaction.atomic
    def handle(self, *args, **options):
        tenant_names = [
            "Rhythm Row Studios",
            "The Soundwave Suites",
            "Melody Loft Co.",
            "Harmonic House",
        ]

        created_count = 0
        skipped_count = 0

        for name in tenant_names:
            tenant, created = Tenant.objects.get_or_create(
                name=name,
                defaults={'is_active': True}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created tenant: {name}'))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f'Tenant {name} already exists.'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(tenant_names)} tenants. '
                f'Created: {created_count}, Skipped: {skipped_count}'
            )
        )
