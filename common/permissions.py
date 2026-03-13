"""
Permission classes for multi-tenant role-based access control.

Role Hierarchy:
- SUPER_ADMIN: Platform management (tenants, genres, global songs)
- ADMIN: Tenant data management (users, playlists, tenant songs)
- LISTENER: Own data access (profile, playlists, song requests)
"""
from rest_framework.permissions import BasePermission
from common.enums import UserRole


class IsSuperAdmin(BasePermission):
    """
    Allows access only to SUPER_ADMIN users.

    Used for:
    - Tenant CRUD
    - Genre CRUD
    - Global song management
    - Admin user creation
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.SUPER_ADMIN


class IsAdmin(BasePermission):
    """
    Allows access only to ADMIN users.

    Used for:
    - Tenant user management
    - Tenant song management
    - Song request review
    - Tenant-song links
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsAdminOrSuperAdmin(BasePermission):
    """Allows access to ADMIN or SUPER_ADMIN users."""


    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        ]


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - ADMIN can access any object in their tenant
    - Owner can access their own object

    Used for: Playlist detail operations
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # SUPER_ADMIN has NO access to tenant data
        if user.role == UserRole.SUPER_ADMIN:
            return False

        # ADMIN can access any object in their tenant
        if user.role == UserRole.ADMIN:
            obj_tenant = getattr(obj, "tenant", None)
            if obj_tenant is None and hasattr(obj, "user"):
                obj_tenant = getattr(obj.user, "tenant", None)
            return obj_tenant == user.tenant

        # LISTENER can only access their own objects
        owner = getattr(obj, "user", None)
        return owner == user



class IsTenantUser(BasePermission):
    """
    Allows access only to users belonging to a tenant (ADMIN or LISTENER).
    Strictly blocks SUPER_ADMIN from accessing tenant-scoped resources.
    """


    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return request.user.role in [UserRole.ADMIN, UserRole.LISTENER]
