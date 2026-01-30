"""
Admin views for user management (delete, restore users).
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status

from common.responses import success_response, error_response
from common.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from common.pagination import DefaultPagination
from users.models import User
from common.enums import UserRole
from music.models.playlist_song_models import PlaylistSong
from users.serializers.user_serializers import SuperAdminAdminSerializer, AdminUserSerializer
from users.filters import SuperAdminAdminsFilter


class AdminRestoreUserAPIView(APIView):
    """Restore soft-deleted user. ADMIN: tenant-scoped users. SUPER_ADMIN: deleted admins only."""
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def post(self, request, user_id):
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                user = User.all_users.get(
                    id=user_id,
                    role=UserRole.ADMIN,
                    deleted_at__isnull=False,
                )
            else:
                user = User.all_users.get(
                    id=user_id,
                    role=UserRole.LISTENER,
                    tenant=request.user.tenant,
                    deleted_at__isnull=False,
                )
        except User.DoesNotExist:
            if request.user.role == UserRole.SUPER_ADMIN:
                return error_response(
                    "Deleted admin not found.",
                    status_code=http_status.HTTP_404_NOT_FOUND,
                )
            return error_response(
                "Deleted user not found.",
                status_code=http_status.HTTP_404_NOT_FOUND,
            )

        user.restore()

        restore_data = request.data.get("restore_data", False)
        if restore_data:
            restored_playlists = user.playlists.filter(
                deleted_at__isnull=False
            ).exclude(deleted_by=user)
            restored_playlists.update(deleted_at=None, deleted_by=None)

            PlaylistSong.objects.filter(
                playlist__in=restored_playlists,
                deleted_at__isnull=False,
            ).exclude(deleted_by=user).update(deleted_at=None, deleted_by=None)

        return success_response(
            message=f"User restored successfully. Data restored: {restore_data}",
            data={
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "restore_data": restore_data,
            },
        )


class SuperAdminListAdminsAPIView(APIView):
    """
    Super Admin endpoint to list all admins across the platform.
    Query params: page, page_size, is_active, name, email, tenant_id (comma-separated).
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        """Get all admins, optionally filtered by tenant_id, is_active, name, email."""
        admins = User.all_users.filter(
            role=UserRole.ADMIN,
            deleted_at__isnull=True
        ).select_related("tenant").order_by("-date_joined")

        try:
            admins = SuperAdminAdminsFilter(
                admins, request.query_params
            ).apply()
        except ValueError as e:
            return error_response(
                str(e),
                status_code=http_status.HTTP_400_BAD_REQUEST,
            )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(admins, request)
        serializer = SuperAdminAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

# Admin APIs
class AdminUserListAPIView(APIView):
    """
    User list API (role-filtered).
    - SUPER_ADMIN: Returns only total count
    - ADMIN: Returns paginated list in tenant
    - LISTENER: 403 Forbidden
    """

    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get(self, request):
        
        
        if request.user.role ==UserRole.SUPER_ADMIN:
            # Super admin gets count only (no PII)
            count = User.objects.count()
            return success_response(message="Total users count retrieved.", data={"total_users": count})
        
        elif request.user.role == UserRole.ADMIN:
            # Admin gets full list in their tenant
            users = User.objects.filter(tenant=request.user.tenant).order_by("-date_joined")
            
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(users, request)
            
            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        else:
            # LISTENER denied
            return error_response("Permission denied.", status_code=http_status.HTTP_403_FORBIDDEN)

        

class AdminUserDetailAPIView(APIView):
    """
    Admin-only API to retrieve or update a specific user in their tenant.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request, id):
        # Admin can only access users in their tenant
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                user = User.objects.get(id=id)
            else:
                user = User.objects.get(id=id, tenant=request.user.tenant)
            if request.user.id == user.id:
                return error_response("Cannot view your own account details. Use /users/me/ endpoint instead.", status_code=http_status.HTTP_400_BAD_REQUEST)

            if request.user.role == UserRole.SUPER_ADMIN and user.role == UserRole.LISTENER:
                return error_response("Super Admin cannot view listener account.", status_code=http_status.HTTP_400_BAD_REQUEST)
            
            serializer = AdminUserSerializer(user)
            return success_response(message="User retrieved.", data=serializer.data)
        except User.DoesNotExist:
            return error_response("User not found.", status_code=http_status.HTTP_404_NOT_FOUND)

    def patch(self, request, id):
        # Admin can only update users in their tenant
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                user = User.objects.get(id=id)
            else:
                user = User.objects.get(id=id, tenant=request.user.tenant)
            
        except User.DoesNotExist:
            return error_response("User not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        
        if request.user.id == user.id:
            return error_response("Cannot update your own account. Use /users/me/ endpoint instead.", status_code=http_status.HTTP_400_BAD_REQUEST)
        if request.user.role == UserRole.SUPER_ADMIN and user.role == UserRole.LISTENER:
            return error_response("Super Admin cannot update listener account.", status_code=http_status.HTTP_400_BAD_REQUEST)
                
        # Admin cannot update other admins (can only view them)
        if user.role == UserRole.ADMIN and user.id != request.user.id and request.user.role != UserRole.SUPER_ADMIN:
            return error_response(
                "Admin cannot update other admin accounts. You can only view their details.",
                status_code=http_status.HTTP_403_FORBIDDEN
            )
        
        # Cannot change role or tenant
        if 'role' in request.data or 'tenant' in request.data:
            return error_response("Cannot change role or tenant.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminUserSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(message="User updated successfully")

    def delete(self, request, id):
        # Get user within the same tenant
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                user = User.objects.get(id=id)
            else:
                user = User.objects.get(id=id, tenant=request.user.tenant)
            
        except User.DoesNotExist:
            return error_response("User not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        
        if user.id == request.user.id:
            return error_response("Cannot delete your own account.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        if user.role == UserRole.ADMIN and request.user.role != UserRole.SUPER_ADMIN:
            return error_response("Admin cannot delete their own or other admin account.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        if user.role == UserRole.LISTENER and request.user.role == UserRole.SUPER_ADMIN:
            return error_response("Super Admin cannot delete their own or other listener account.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        if user.role == UserRole.SUPER_ADMIN and request.user.role == UserRole.SUPER_ADMIN:
            return error_response("Super Admin cannot delete their own or other super admin account.", status_code=http_status.HTTP_400_BAD_REQUEST)
        
        # Soft delete with admin tracking
        user.delete(deleted_by=request.user)
        
        return success_response(message="User deleted successfully.")