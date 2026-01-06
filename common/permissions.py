from rest_framework.permissions import BasePermission
from common.enums import UserRole

class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Admin can access any object
    - Owner can access their own object
    """
    message = "You do not have permission to perform this action."
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role == UserRole.ADMIN:
            return True

        # Object must have `user` attribute for ownership check
        owner = getattr(obj, "user", None)
        return owner == request.user

class IsAdmin(BasePermission):
    """
    Allows access only to admin users.
    """
    message = "Admin access required."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


