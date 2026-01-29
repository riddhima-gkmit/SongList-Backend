from django.db import transaction
from users.models import User
from common.enums import UserRole


def register_or_rewrite_user(*, tenant, data):
    """
    Register a new user or rewrite an existing inactive/soft-deleted user.
    
    Rules:
    - Username is globally unique
    - Email is tenant-wise unique
    - Can rewrite user if: inactive/unverified OR soft-deleted (by self)
    - Cannot use username if it's taken by an active user in ANY tenant
    - Cannot use username if it's taken by a user in a different tenant (even if inactive)
    """
    email = data["email"]
    username = data["username"]
    
    # Find user by email in the same tenant (for rewrite case)
    user_by_email = User.all_users.filter(
        email=email,
        tenant=tenant
    ).first()
    
    # Find user by username globally (to check uniqueness)
    user_by_username = User.all_users.filter(username=username).first()
    
    with transaction.atomic():
        # Case 1: User exists in same tenant with same email
        if user_by_email:
            # Check if account is active and verified
            if user_by_email.is_active and user_by_email.is_verified:
                raise ValueError("Account already exists. Please login.")
            
            # Check if account was disabled by admin
            if user_by_email.deleted_at and user_by_email.deleted_by_id != user_by_email.id:
                raise PermissionError("Account disabled by admin.")
            
            # Check username availability for rewrite
            # Username can be changed if:
            # - It's the same username (no change) - always allowed
            # - OR username is not taken globally - allowed
            # - OR username is taken by this same user (rewriting their own account) - allowed
            # Username cannot be changed if:
            # - Taken by user in different tenant - not allowed
            # - Taken by active/verified user in same tenant - not allowed
            # - Taken by inactive user in same tenant (might be reactivated) - not allowed
            if username != user_by_email.username:
                if user_by_username and user_by_username.id != user_by_email.id:
                    # Username is taken by a different user - reject
                    raise ValueError("Username already taken.")
            
            # Rewrite existing user
            user_by_email.username = username
            user_by_email.first_name = data.get("first_name", "")
            user_by_email.last_name = data.get("last_name", "")
            user_by_email.phone_no = data.get("phone_no", "")
            user_by_email.set_password(data["password"])
            
            # Reset user state
            user_by_email.is_active = False
            user_by_email.is_verified = False
            user_by_email.deleted_at = None
            user_by_email.deleted_by = None
            
            user_by_email.save()
            return user_by_email, "rewritten"
        
        # Case 2: New user registration
        # Check if username is available globally
        if user_by_username:
            # Username is taken
            if user_by_username.tenant != tenant:
                # Username taken by user in different tenant - not allowed
                raise ValueError("Username already taken.")
            elif user_by_username.is_active and user_by_username.is_verified:
                # Username taken by active user in same tenant - not allowed
                raise ValueError("Username already taken.")
            # If username is taken by inactive/unverified user in same tenant,
            # we still can't use it (that user might be reactivated)
            # Only allow if it's the same email (handled in Case 1 above)
            else:
                raise ValueError("Username already taken.")
        
        # Create new user
        try:
            user = User.objects.create_user(
                username=username,
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
