from django.db import transaction
from users.models import User
from common.enums import UserRole

def register_or_rewrite_user(*, tenant, data):
    email = data["email"]
    user = User.all_users.filter(username=data["username"]).first()
    if user and user.email != email:
        raise ValueError("Username already taken.")
        
    user = User.all_users.filter(
        email=email,
        tenant=tenant
    ).first()


    with transaction.atomic():

        if user and user.is_active and user.is_verified:
            raise ValueError("Account already exists. Please login.")

        if user and user.deleted_at and user.deleted_by_id != user.id:
            raise PermissionError("Account disabled by admin.")

        if user:
            user.username = data["username"]
            user.first_name = data.get("first_name", "")
            user.last_name = data.get("last_name", "")
            user.phone_no = data.get("phone_no", "")
            user.set_password(data["password"])

            # IMPORTANT
            user.is_active = False
            user.is_verified = False
            user.deleted_at = None
            user.deleted_by = None

            user.save()
            return user, "rewritten"
        try:
            user = User.objects.create_user(
                username=data["username"],
                email=email,
                password=data["password"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                phone_no=data.get("phone_no", ""),
                tenant=tenant,
                role=UserRole.LISTENER,
                is_active=False,
                is_verified=False
            )
        except Exception as e:
            raise ValueError(f"Failed to create user: {e}")

        return user, "created"
