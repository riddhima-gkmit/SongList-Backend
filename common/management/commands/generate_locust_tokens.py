"""
Management command: generate_locust_tokens
------------------------------------------
Queries the database for up to N active + verified users (any role),
mints fresh JWT access+refresh tokens for each of them using SimpleJWT, and
writes the result to locust/tokens.json so that the Locust load-test suite can
pick them up without touching the auth OTP flow.

Default role: LISTENER  — required for the playlist load-test suite which
targets POST /api/v1/playlists/, GET /api/v1/playlists/, GET /api/v1/users/me/.
SUPER_ADMIN is blocked from playlist endpoints; ADMIN cannot create playlists
for themselves.

Usage:
    uv run python manage.py generate_locust_tokens
    uv run python manage.py generate_locust_tokens --count 3
    uv run python manage.py generate_locust_tokens --roles LISTENER ADMIN
    uv run python manage.py generate_locust_tokens --output /tmp/tokens.json
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from rest_framework_simplejwt.tokens import RefreshToken

from common.enums import UserRole
from users.models import User


class Command(BaseCommand):
    help = "Mint JWT tokens for active users (default: LISTENER) and write to locust/tokens.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of users to generate tokens for (default: 5)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output file path (default: <project-root>/locust/tokens.json)",
        )
        parser.add_argument(
            "--roles",
            nargs="+",
            choices=[UserRole.LISTENER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            default=[UserRole.LISTENER],
            help="Roles to include (default: LISTENER)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        roles = options["roles"]

        # Resolve output path
        if options["output"]:
            output_path = Path(options["output"])
        else:
            project_root = Path(__file__).resolve().parents[3]
            output_path = project_root / "locust" / "tokens.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Eligible users: active, email-verified, not soft-deleted, correct role
        users = (
            User.objects.filter(
                role__in=roles,
                is_active=True,
                is_verified=True,
                deleted_at__isnull=True,
            )
            .select_related("tenant")
            .order_by("role", "created_at")[:count]
        )

        if not users:
            raise CommandError(
                f"No active + verified users found with roles {roles}. "
                "Run seed commands first or create users manually."
            )

        if len(users) < count:
            self.stdout.write(
                self.style.WARNING(
                    f"Only {len(users)} eligible user(s) found (requested {count}). "
                    "Generating tokens for all available users."
                )
            )

        tokens = []
        for user in users:
            refresh = RefreshToken.for_user(user)
            entry = {
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "tenant_name": user.tenant.name if user.tenant else None,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
            tokens.append(entry)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [{user.role}] {user.email}"
                    + (f" (tenant: {user.tenant.name})" if user.tenant else "")
                )
            )

        output_path.write_text(json.dumps(tokens, indent=2))

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{len(tokens)} token(s) written to {output_path}"
            )
        )
