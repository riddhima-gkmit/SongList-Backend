from django.urls import path
from users.views.auth import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
)
from users.views.user import (
    UserMeAPIView,
    ChangePasswordAPIView,
    AdminUserListAPIView,
    AdminUserDetailAPIView,
)

urlpatterns = [
    # Authentication
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),

    # User Self-Service
    path("users/me/", UserMeAPIView.as_view(), name="user-me"),
    path("users/me/change-password/", ChangePasswordAPIView.as_view(), name="change-password"),

    # Admin User Management
    path("users/", AdminUserListAPIView.as_view(), name="admin-user-list"),
    path("users/<uuid:id>/", AdminUserDetailAPIView.as_view(), name="admin-user-detail"),
]
