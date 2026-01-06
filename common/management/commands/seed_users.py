from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from common.enums import UserRole

class Command(BaseCommand):
    help = 'Seeds the database with 5 regular users (user1 to user5)'

    @transaction.atomic
    def handle(self, *args, **options):
        password = "password123"  # Default password for all seeded users
        created_count = 0

        for i in range(1, 6):
            username = f'user{i}'
            email = f'user{i}@example.com'
            
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=f'User',
                    last_name=f'{i}',
                    role=UserRole.USER
                )
                created_count += 1
                self.stdout.write(f'Created user: {username}')
            else:
                self.stdout.write(f'User {username} already exists.')

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} regular users.'))
