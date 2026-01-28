from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import F

from common.permissions import IsAdminOrSuperAdmin
from common.responses import success_response, error_response
from common.pagination import DefaultPagination
from common.enums import UserRole
from users.serializers.user_create_serializers import UserCreateSerializer
from users.serializers.user_serializers import AdminUserSerializer
from users.serializers.deleted_user_serializers import DeletedUserSerializer
from users.models import User
from users.filters import UserListFilter


class UserCreateAPIView(APIView):
    """Create/list users. GET supports filters: page, page_size, is_active, name, email."""
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request):
        """Get users list. ADMIN: paginated list; SUPER_ADMIN: count only."""
        if request.user.role == UserRole.SUPER_ADMIN:
            users = User.objects.all()
            users = UserListFilter(users, request.query_params).apply()
            count = users.count()
            return success_response(message="Total users count retrieved.", data={"total_users": count})

        elif request.user.role == UserRole.ADMIN:
            users = User.objects.filter(tenant=request.user.tenant).order_by("-date_joined")
            users = UserListFilter(users, request.query_params).apply()

            paginator = DefaultPagination()
            page = paginator.paginate_queryset(users, request)

            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        else:
            return error_response("Permission denied.", status_code=status.HTTP_403_FORBIDDEN)
    
    def post(self, request):
        """Create user."""
        if request.user.role == UserRole.ADMIN:
            role_in_data = request.data.get('role')
            if role_in_data == UserRole.ADMIN:
                return error_response(
                    "Admin cannot create other admin accounts. Only Super Admin can create admins.",
                    status_code=status.HTTP_403_FORBIDDEN
                )
        
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return success_response(
            message="User created successfully. Verification email sent.",
            data={
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role
            },
            status_code=status.HTTP_201_CREATED
        )


class DeletedUsersListAPIView(APIView):
    """List deleted users. ADMIN: deleted users in their tenant. SUPER_ADMIN: deleted admins platform-wide."""
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request):
        """Get deleted users (ADMIN: tenant-scoped; SUPER_ADMIN: deleted admins only)."""
        if request.user.role == UserRole.SUPER_ADMIN:
            deleted_users = User.all_users.filter(
                role=UserRole.ADMIN,
                deleted_at__isnull=False,
            ).select_related('tenant', 'deleted_by').order_by('-deleted_at')
        else:
            deleted_users = User.all_users.filter(
                tenant=request.user.tenant,
                deleted_at__isnull=False,
            ).select_related('tenant', 'deleted_by').order_by('-deleted_at')

        deletion_type = request.query_params.get('deletion_type')
        if deletion_type == 'self':
            deleted_users = deleted_users.filter(deleted_by=F('id'))
        elif deletion_type == 'admin':
            deleted_users = deleted_users.exclude(deleted_by=F('id'))

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(deleted_users, request)

        serializer = DeletedUserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
