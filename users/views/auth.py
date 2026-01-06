from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ValidationError
from rest_framework.exceptions import APIException

from ..serializers import (
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer
)

class RegisterAPIView(APIView):
    """
    Register a new user.
    Role is always USER by default.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Registration failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class LoginAPIView(APIView):
    """
    Authenticate user and return JWT tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            return Response(
                serializer.validated_data,
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Login failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class LogoutAPIView(APIView):
    """
    Logout user by blacklisting refresh token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = LogoutSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()

            return Response(
                {"message": "Logout successful"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except AttributeError:
            return Response(
                {"error": "Token blacklist not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except APIException:
            raise
        except Exception:
            return Response(
                {"error": "Logout failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
