"""
URL configuration for songlist_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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