"""
Management command: create_locust_users
----------------------------------------
Creates a dedicated "Load Test Tenant" (if not already present), provisions N
LISTENER load-test users inside it, mints fresh JWT tokens for each one, and
writes the result to locust/tokens.json so the Locust suite can use them.

Differences vs. generate_locust_tokens:
  - generate_locust_tokens  → reads *existing* users from the DB
  - create_locust_users     → *creates* test users (idempotent) then mints tokens

Why LISTENER (not ADMIN or SUPER_ADMIN)?
  The playlist load-test targets three endpoints:
    GET  /api/v1/playlists/  — list own playlists
    POST /api/v1/playlists/  — create a playlist
    GET  /api/v1/users/me/   — view own profile

  SUPER_ADMIN is explicitly blocked (403) on all playlist endpoints.
  ADMIN can only create playlists for *other* users (user_id required),
  not for themselves. LISTENER creates / reads their own playlists directly,
  which is the natural fit for all three operations.

Usage:
    uv run python manage.py create_locust_users
    uv run python manage.py create_locust_users --count 5
    uv run python manage.py create_locust_users --tenant-name "My Load Test Org"
    uv run python manage.py create_locust_users --append   # merge into existing tokens.json
    uv run python manage.py create_locust_users --output /tmp/tokens.json
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from common.enums import UserRole
from tenants.models import Tenant
from users.models import User


DEFAULT_PASSWORD = "LoadTest@123"


class Command(BaseCommand):
    help = "Create load-test LISTENER users + mint JWT tokens → locust/tokens.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of load-test users to create (default: 10)",
        )
        parser.add_argument(
            "--tenant-name",
            type=str,
            default="Load Test Tenant",
            help='Name of the load-test tenant (default: "Load Test Tenant")',
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output file path (default: <project-root>/locust/tokens.json)",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            default=False,
            help="Append to an existing tokens.json instead of overwriting it",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        tenant_name = options["tenant_name"]

        # ── Resolve output path ───────────────────────────────────────────────
        if options["output"]:
            output_path = Path(options["output"])
        else:
            project_root = Path(__file__).resolve().parents[3]
            output_path = project_root / "locust" / "tokens.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ── 1. Ensure the load-test tenant exists ─────────────────────────────
        tenant, t_created = Tenant.objects.get_or_create(
            name=tenant_name,
            defaults={"is_active": True},
        )
        if t_created:
            self.stdout.write(self.style.SUCCESS(f"Created tenant: {tenant.name}"))
        else:
            self.stdout.write(f"Using existing tenant: {tenant.name}")

        # ── 2. Create load-test LISTENER users (idempotent) ──────────────────
        tokens = []
        for i in range(1, count + 1):
            username = f"loadtest_user_{i}"
            email = f"loadtest_{i}@example.com"

            user, u_created = User.all_users.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "tenant": tenant,
                    "role": UserRole.LISTENER,
                    "is_verified": True,
                    "is_active": True,
                },
            )

            if u_created:
                user.set_password(DEFAULT_PASSWORD)
                # Ensure required flags are set even if defaults are overridden
                user.is_active = True
                user.is_verified = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f"  Created  {username} ({email})"))
            else:
                # Bring existing user back to a usable state
                needs_save = False
                if not user.is_active:
                    user.is_active = True
                    needs_save = True
                if not user.is_verified:
                    user.is_verified = True
                    needs_save = True
                if user.deleted_at is not None:
                    user.deleted_at = None
                    user.deleted_by = None
                    needs_save = True
                if needs_save:
                    user.save()
                self.stdout.write(f"  Reusing  {username} ({email})")

            # ── 3. Mint JWT tokens ────────────────────────────────────────────
            refresh = RefreshToken.for_user(user)
            tokens.append(
                {
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "tenant_id": str(user.tenant_id),
                    "tenant_name": tenant.name,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }
            )

        # ── 4. Write tokens.json ──────────────────────────────────────────────
        if options["append"] and output_path.exists():
            try:
                existing = json.loads(output_path.read_text())
                if isinstance(existing, list):
                    tokens = existing + tokens
            except (json.JSONDecodeError, OSError):
                pass  # Overwrite if the file is corrupt

        output_path.write_text(json.dumps(tokens, indent=2))

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{len(tokens)} token(s) written to {output_path}\n"
                f"Tenant : {tenant.name}\n"
                f"Role   : {UserRole.LISTENER}\n"
                f"Password (for manual login): {DEFAULT_PASSWORD}"
            )
        )
