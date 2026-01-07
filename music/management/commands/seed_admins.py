from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from common.enums import UserRole

class Command(BaseCommand):
    help = 'Seeds the database with 1 admin user'

    @transaction.atomic
    def handle(self, *args, **options):
        username = "admin"
        email = "admin@example.com"
        password = "Gkmit@123"

        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name="Admin",
                last_name="User",
                role=UserRole.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin {username} already exists.'))
