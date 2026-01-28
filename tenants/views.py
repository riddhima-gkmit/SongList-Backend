from rest_framework.views import APIView, Response
from rest_framework import status

from common.enums import UserRole
from common.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from common.pagination import DefaultPagination
from common.responses import success_response, error_response
from tenants.models import Tenant
from tenants.serializers import TenantSerializer


class TenantListCreateAPIView(APIView):
    """
    GET: List all tenants
    POST: Create a new tenant
    """

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        # List only active tenants (default manager already filters)
        queryset = Tenant.all_tenants.all().order_by("name")

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = TenantSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()

        return success_response(
            "Tenant created successfully",
            TenantSerializer(tenant).data,
            status.HTTP_201_CREATED,
        )


class TenantDetailAPIView(APIView):
    """GET, PATCH, DELETE for single tenant."""
    
    def get_permissions(self):
        """Return different permissions based on HTTP method."""
        if self.request.method == 'GET':
            # GET: Allow both admin and super admin
            return [IsAdminOrSuperAdmin()]
        else:
            # PATCH, DELETE: Only super admin
            return [IsSuperAdmin()]

    def get(self, request, id):
        try:
            # GET: Only active tenants (default manager already filters)
            if request.user.role == UserRole.SUPER_ADMIN:
                tenant = Tenant.all_tenants.get(id=id, deleted_at__isnull=True)
            else:
                tenant = Tenant.objects.get(id=id)
            serializer = TenantSerializer(tenant)
            return success_response("Tenant retrieved", serializer.data)
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=status.HTTP_404_NOT_FOUND)

    def patch(self, request, id):
        try:
            # PATCH: Super admin can update inactive tenants too
            tenant = Tenant.all_tenants.get(id=id, deleted_at__isnull=True)
            serializer = TenantSerializer(tenant, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response("Tenant updated successfully", serializer.data)
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id):
        try:
            # DELETE: Super admin can delete inactive tenants too
            tenant = Tenant.all_tenants.get(id=id, deleted_at__isnull=True)
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=status.HTTP_404_NOT_FOUND)
            
        # Check if tenant has any active users
        active_users_count = tenant.users.filter(deleted_at__isnull=True).count()
        if active_users_count > 0:
            return error_response(
                f"Cannot delete tenant. It has {active_users_count} active user(s).",
                {"detail": "Remove all active users before deleting the tenant"},
                status.HTTP_400_BAD_REQUEST,
            )

        tenant.delete(deleted_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TenantActivateAPIView(APIView):
    """Activate a tenant."""

    permission_classes = [IsSuperAdmin]

    def patch(self, request, id):
        try:
            # Activate: Need to access inactive tenants
            tenant = Tenant.all_tenants.get(id=id, deleted_at__isnull=True)
            tenant.activate()
            return success_response("Tenant activated successfully")
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=status.HTTP_404_NOT_FOUND)


class TenantDeactivateAPIView(APIView):
    """Deactivate a tenant."""

    permission_classes = [IsSuperAdmin]

    def patch(self, request, id):
        try:
            # Deactivate: Need to access active tenants (but use all_tenants for consistency)
            tenant = Tenant.all_tenants.get(id=id, deleted_at__isnull=True)
            tenant.deactivate()
            return success_response("Tenant deactivated successfully")
        except Tenant.DoesNotExist:
            return error_response("Tenant not found.", status_code=status.HTTP_404_NOT_FOUND)
