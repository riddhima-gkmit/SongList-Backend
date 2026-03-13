from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from users.serializers import UserSerializer, ChangePasswordSerializer
from common.responses import success_response, error_response
from common.constants import ACCESS_TOKEN_DENYLIST_TTL
from common.enums import UserRole
from django.core.cache import cache

# User Self-Service APIs
class UserMeAPIView(APIView):
    """
    Retrieve, update, or delete the authenticated user's profile.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(message="Profile retrieved.", data=serializer.data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(message="Profile updated successfully")

    def delete(self, request):
        """
        Soft delete the authenticated user's account.

        Admin and Super Adminusers are NOT allowed to delete their own accounts.
        """
        if request.user.role == UserRole.ADMIN or request.user.role == UserRole.SUPER_ADMIN:
            return error_response("Admin and Super Admin accounts cannot be deleted.", status_code=http_status.HTTP_403_FORBIDDEN)

        request.user.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class ChangePasswordAPIView(APIView):
    """
    Change password for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return error_response("Old password is incorrect", status_code=http_status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()

        # Denylist current access token for 12 minutes
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            cache.set(f"denylist_{access_token}", True, timeout=ACCESS_TOKEN_DENYLIST_TTL)

        return success_response(
            message="Your password is changed and you are logged out. Please login again."
        )


