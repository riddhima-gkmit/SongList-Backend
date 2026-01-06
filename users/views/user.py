from django.http import Http404
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.exceptions import APIException

from users.models import User
from common.permissions import IsAdmin
from users.serializers import UserSerializer, ChangePasswordSerializer
from users.serializers.user import AdminUserSerializer
from common.pagination import DefaultPagination

# User Self-Service APIs
class UserMeAPIView(APIView):
    """
    Retrieve, update, or delete the authenticated user's profile.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            serializer = UserSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to retrieve profile."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request):
        try:
            serializer = UserSerializer(
                request.user,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "Profile updated successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to update profile."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request):
        """
        Soft delete the authenticated user's account.

        Admin users are NOT allowed to delete their own accounts.
        """
        try:
            if request.user.is_admin:
                return Response(
                    {"error": "Admin accounts cannot be deleted."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            request.user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to delete account."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChangePasswordAPIView(APIView):
    """
    Change password for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = ChangePasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if not request.user.check_password(
                serializer.validated_data["old_password"]
            ):
                return Response(
                    {"error": "Old password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            request.user.set_password(
                serializer.validated_data["new_password"]
            )
            request.user.save()

            return Response(
                {"message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Password change failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Admin APIs
class AdminUserListAPIView(APIView):
    """
    Admin-only API to retrieve a paginated list of all users.
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = DefaultPagination

    def get(self, request):
        try:
            users = User.objects.all().order_by("-date_joined")

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(users, request)

            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to retrieve users."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        

class AdminUserDetailAPIView(APIView):
    """
    Admin-only API to retrieve, update, or soft-delete a specific user.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, id):
        try:
            user = get_object_or_404(User, id=id)
            serializer = AdminUserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to retrieve user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, id):
        try:
            user = get_object_or_404(User, id=id)
            serializer = AdminUserSerializer(
                user,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "User updated successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Http404:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to update user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, id):
        try:
            user = get_object_or_404(User, id=id)

            # Prevent admin deleting themselves
            if user.id == request.user.id:
                return Response(
                    {"error": "Admin cannot delete their own account."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            user.delete()  # soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Http404:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Failed to delete user."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
