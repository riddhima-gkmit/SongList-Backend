"""
Tenant URLs - SUPER_ADMIN only.
"""
from django.urls import path
from tenants.views import (
    TenantListCreateAPIView,
    TenantDetailAPIView,
    TenantActivateAPIView,
    TenantDeactivateAPIView,
)

urlpatterns = [
    path("tenants/", TenantListCreateAPIView.as_view(), name="tenant-list"),
    path("tenants/<uuid:id>/", TenantDetailAPIView.as_view(), name="tenant-detail"),
    path(
        "tenants/<uuid:id>/activate/",
        TenantActivateAPIView.as_view(),
        name="tenant-activate",
    ),
    path(
        "tenants/<uuid:id>/deactivate/",
        TenantDeactivateAPIView.as_view(),
        name="tenant-deactivate",
    ),
]
