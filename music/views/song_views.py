from django.core.cache import cache
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from music.models.song_models import Song
from music.serializers.song_serializers import SongSerializer
from music.filters import SongQueryFilter
from common.pagination import DefaultPagination
from common.enums import UserRole
from common.responses import error_response, success_response
from common.cache_utils import (
    get_songs_list_cache_key,
    get_song_list_params_hash,
    invalidate_songs_list_cache,
    invalidate_tenant_songs_list_cache,
    SONGS_LIST_CACHE_TTL,
)
from music.models.tenant_song_models import TenantSong


class SongAPIView(APIView):
    """List/create songs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List songs (cached)."""
        try:
            if request.user.role == UserRole.LISTENER:
                return error_response(
                    "LISTENER users cannot access songs directly. Please use /api/v1/tenant/songs/ endpoint instead.",
                    status_code=status.HTTP_403_FORBIDDEN
                )

            paginator = DefaultPagination()
            page_num = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            params_hash = get_song_list_params_hash(request.query_params)
            role = str(request.user.role)
            tenant_id = str(request.user.tenant_id) if request.user.tenant_id else None
            cache_key = get_songs_list_cache_key(role, tenant_id, params_hash, page_num, page_size)

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            if request.user.role == UserRole.SUPER_ADMIN:
                queryset = Song.objects.filter(visibility='GLOBAL')
            elif request.user.role == UserRole.ADMIN:
                queryset = Song.objects.filter(
                    Q(visibility='TENANT', tenant=request.user.tenant) |
                    Q(visibility='GLOBAL')
                )

            queryset = SongQueryFilter(queryset, request.query_params).apply()
            page = paginator.paginate_queryset(queryset, request)
            serializer = SongSerializer(page, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            cache.set(cache_key, response_data, SONGS_LIST_CACHE_TTL)
            return Response(response_data)

        except Exception as e:
            return error_response(
                "Failed to fetch songs.",
                str(e),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Create song."""
        if request.user.role == UserRole.ADMIN:
            # Check if tenant has premium subscription
            tenant = request.user.tenant
            if not tenant or not tenant.is_premium:
                return error_response(
                    "Premium subscription required to add songs. Please upgrade to premium to add songs.",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            request.data['visibility'] = 'TENANT'
            request.data['tenant'] = tenant.id
        elif request.user.role == UserRole.SUPER_ADMIN:
            request.data['visibility'] = 'GLOBAL'
        else:
            return error_response("Only admin or super admin can create songs.", status_code=status.HTTP_403_FORBIDDEN)
        
        serializer = SongSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        song = serializer.save(user=request.user)
        
        if request.user.role == UserRole.ADMIN:
            TenantSong.objects.get_or_create(
                tenant=request.user.tenant,
                song=song
            )
            invalidate_tenant_songs_list_cache(str(request.user.tenant_id))

        invalidate_songs_list_cache()
        return success_response(
            message="Song created successfully.",
            data=SongSerializer(song).data,
            status_code=status.HTTP_201_CREATED
        )


class SongDetailAPIView(APIView):
    """Get/update/delete song."""
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """Get song."""
        try:
            song = Song.objects.get(id=id)
        except Song.DoesNotExist:
            return error_response("Song not found.", status_code=status.HTTP_404_NOT_FOUND)

        if request.user.role == UserRole.LISTENER:
            return error_response(
                "LISTENER users cannot access song details directly. Please use /api/v1/tenant/songs/{id}/ endpoint instead.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if request.user.role == UserRole.SUPER_ADMIN:
            if song.visibility != 'GLOBAL':
                return error_response("Song not found.", status_code=status.HTTP_404_NOT_FOUND)
        elif request.user.role == UserRole.ADMIN:
            if song.visibility == 'TENANT' and song.tenant != request.user.tenant:
                return error_response("Song not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = SongSerializer(song)
        return success_response("Song retrieved.", serializer.data)

    def patch(self, request, id):
        """Update song."""
        try:
            song = Song.objects.get(id=id)
        except Song.DoesNotExist:
            return error_response("Song not found.", status_code=status.HTTP_404_NOT_FOUND)
        
        if request.user.role == UserRole.SUPER_ADMIN:
            if song.visibility != 'GLOBAL':
                return error_response("Super admin can only update GLOBAL songs.", status_code=status.HTTP_403_FORBIDDEN)
        elif request.user.role == UserRole.ADMIN:
            if song.visibility != 'TENANT' or song.tenant != request.user.tenant:
                return error_response("Admin can only update TENANT songs in own tenant.", status_code=status.HTTP_403_FORBIDDEN)
        else:
            return error_response("Permission denied.", status_code=status.HTTP_403_FORBIDDEN)

        serializer = SongSerializer(song, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        invalidate_songs_list_cache()
        if song.tenant_id:
            invalidate_tenant_songs_list_cache(str(song.tenant_id))
        return success_response("Song updated successfully", serializer.data)

    def delete(self, request, id):
        """Delete song."""
        try:
            song = Song.objects.get(id=id)
        except Song.DoesNotExist:
            return error_response("Song not found.", status_code=status.HTTP_404_NOT_FOUND)

        if request.user.role == UserRole.SUPER_ADMIN:
            if song.visibility != 'GLOBAL':
                return error_response("Super admin can only delete GLOBAL songs.", status_code=status.HTTP_403_FORBIDDEN)
        elif request.user.role == UserRole.ADMIN:
            if song.visibility != 'TENANT' or song.tenant != request.user.tenant:
                return error_response("Admin can only delete TENANT songs in own tenant.", status_code=status.HTTP_403_FORBIDDEN)
        else:
            return error_response("Permission denied.", status_code=status.HTTP_403_FORBIDDEN)

        tenant_id = str(song.tenant_id) if song.tenant_id else None
        song.delete(deleted_by=request.user)
        invalidate_songs_list_cache()
        if tenant_id:
            invalidate_tenant_songs_list_cache(tenant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
