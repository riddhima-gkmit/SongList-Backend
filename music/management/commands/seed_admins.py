import os

from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from common.enums import UserRole


class Command(BaseCommand):
    help = 'Seeds the database with 1 admin user'

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME")
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        first_name = os.getenv("ADMIN_FIRST_NAME")
        last_name = os.getenv("ADMIN_LAST_NAME")

        if not password:
            self.stdout.write(self.style.ERROR('ADMIN_PASSWORD environment variable is not set.'))
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin {username} already exists.'))
