from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Django admin (optional, mainly for debugging)
    path("admin/", admin.site.urls),

    # User & Auth APIs
    path("api/v1/", include("users.urls")),

    # Music APIs (songs, playlists, reviews)
    path("api/v1/", include("music.urls")),

    # Tenant Management APIs (SUPER_ADMIN only)
    path("api/v1/", include("tenants.urls")),

    # Payment APIs
    path("api/v1/payments/", include("payments.urls")),

    # Refresh token
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]