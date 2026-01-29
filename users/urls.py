"""
Users app URLs with tenant-scoped endpoints.
"""
from django.urls import path
from users.views.auth_views import (
    RegisterAPIView,
    VerifyEmailAPIView,
    LoginAPIView,
    VerifyLoginOTPAPIView,
    SuperAdminLoginAPIView,
    SuperAdminVerifyLoginOTPAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    LogoutAPIView,
)
from users.views.resend_verification_views import ResendVerificationEmailAPIView
from users.views.admin_views import (
    AdminUserDetailAPIView,
    AdminRestoreUserAPIView,
    SuperAdminListAdminsAPIView,
)
from users.views.user_views import UserMeAPIView, ChangePasswordAPIView
from users.views.user_management_views import UserCreateAPIView, DeletedUsersListAPIView
from users.views.template_views import ForgotPasswordView, VerifyEmailView


urlpatterns = [
    # Template views
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password_page'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email_page'),
    
    # Authentication endpoints (tenant-scoped)
    path('tenant/<uuid:tenant_id>/auth/register/', RegisterAPIView.as_view(), name='register'),
    path('tenant/<uuid:tenant_id>/auth/verify-email/', VerifyEmailAPIView.as_view(), name='verify_email'),
    path('tenant/<uuid:tenant_id>/auth/resend-verification/', ResendVerificationEmailAPIView.as_view(), name='resend_verification'),
    path('tenant/<uuid:tenant_id>/auth/login/', LoginAPIView.as_view(), name='login'),
    path('tenant/<uuid:tenant_id>/auth/login/verify-otp/', VerifyLoginOTPAPIView.as_view(), name='login_verify_otp'),
    path('tenant/<uuid:tenant_id>/auth/password-reset/', PasswordResetRequestAPIView.as_view(), name='password_reset_request'),
    path('tenant/<uuid:tenant_id>/auth/password-reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='password_reset_confirm'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),
    
    # Super Admin Authentication
    path('auth/super-admin/login/', SuperAdminLoginAPIView.as_view(), name='super_admin_login'),
    path('auth/super-admin/login/verify-otp/', SuperAdminVerifyLoginOTPAPIView.as_view(), name='super_admin_verify_otp'),
    
    # User Self-Service
    path("users/me/", UserMeAPIView.as_view(), name="user-me"),
    path("users/me/change-password/", ChangePasswordAPIView.as_view(), name="change-password"),
    
    # User Management (Admin/Super Admin)
    path('users/', UserCreateAPIView.as_view(), name='user_create'),  # POST only, GET for admin/super_admin
    path('users/deleted/', DeletedUsersListAPIView.as_view(), name='deleted_users_list'),  # Admin or Super Admin
    path('users/<uuid:id>/', AdminUserDetailAPIView.as_view(), name='user-detail'),  # Admin or super admin only
    path('users/<uuid:user_id>/restore/', AdminRestoreUserAPIView.as_view(), name='restore_user'),  # Admin or Super Admin
    
    # Super Admin - List All Admins
    path('super-admin/admins/', SuperAdminListAdminsAPIView.as_view(), name='super_admin_list_admins'),
]
