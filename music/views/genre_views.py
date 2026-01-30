"""Genre views."""
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from common.enums import UserRole
from common.responses import success_response, error_response
from common.pagination import DefaultPagination
from common.cache_utils import (
    get_genres_list_cache_key,
    invalidate_genres_list_cache,
)
from music.models.genre_models import Genre
from music.serializers.genre_serializers import GenreSerializer
from common.constants import GENRES_LIST_CACHE_TTL

class GenreListCreateAPIView(APIView):
    """List/create genres."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List genres (cached)."""
        if request.user.role == UserRole.LISTENER:
            return error_response("Listeners cannot access genre APIs.", status_code=status.HTTP_403_FORBIDDEN)

        paginator = DefaultPagination()
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        cache_key = get_genres_list_cache_key(page_num, page_size)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        genres = Genre.objects.all()
        page = paginator.paginate_queryset(genres, request)
        serializer = GenreSerializer(page, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        cache.set(cache_key, response_data, GENRES_LIST_CACHE_TTL)
        return Response(response_data)

    def post(self, request):
        """Create genre."""
        if request.user.role != UserRole.SUPER_ADMIN:
            return error_response("Only super admin can create genres.", status_code=status.HTTP_403_FORBIDDEN)

        serializer = GenreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_genres_list_cache()
        return success_response(
            message="Genre created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class GenreDetailAPIView(APIView):
    """Get/update/delete genre."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """Get genre."""
        if request.user.role == UserRole.LISTENER:
            return error_response("Listeners cannot access genre APIs.", status_code=status.HTTP_403_FORBIDDEN)
        
        try:
            genre = Genre.objects.get(id=id)
            serializer = GenreSerializer(genre)
            return success_response(message="Genre retrieved.", data=serializer.data)
        except Genre.DoesNotExist:
            return error_response("Genre not found.", status_code=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, id):
        """Update genre."""
        if request.user.role != UserRole.SUPER_ADMIN:
            return error_response("Only super admin can update genres.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            genre = Genre.objects.get(id=id)
            serializer = GenreSerializer(genre, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            invalidate_genres_list_cache()
            return success_response(message="Genre updated successfully.")
        except Genre.DoesNotExist:
            return error_response("Genre not found.", status_code=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, id):
        """Delete genre."""
        if request.user.role != UserRole.SUPER_ADMIN:
            return error_response("Only super admin can delete genres.", status_code=status.HTTP_403_FORBIDDEN)
        
        try:
            genre = Genre.objects.get(id=id)
            genre.delete()
            invalidate_genres_list_cache()
            return success_response(message="Genre deleted successfully.", status_code=status.HTTP_204_NO_CONTENT)
        except Genre.DoesNotExist:
            return error_response("Genre not found.", status_code=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
