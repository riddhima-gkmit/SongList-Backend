from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from music.models.song_models import Song
from music.serializers.song_serializers import SongSerializer
from music.filters import SongQueryFilter
from common.pagination import DefaultPagination
from common.enums import UserRole
from common.responses import error_response, success_response
from music.models.tenant_song_models import TenantSong


class SongAPIView(APIView):
    """List/create songs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List songs."""
        try:
            if request.user.role == UserRole.LISTENER:
                return error_response(
                    "LISTENER users cannot access songs directly. Please use /api/v1/tenant/songs/ endpoint instead.",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            if request.user.role == UserRole.SUPER_ADMIN:
                queryset = Song.objects.filter(visibility='GLOBAL')
            elif request.user.role == UserRole.ADMIN:
                queryset = Song.objects.filter(
                    Q(visibility='TENANT', tenant=request.user.tenant) |
                    Q(visibility='GLOBAL')
                )

            queryset = SongQueryFilter(queryset, request.query_params).apply()

            paginator = DefaultPagination()
            page = paginator.paginate_queryset(queryset, request)

            serializer = SongSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

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

        song.delete(deleted_by=request.user)
        return success_response("Song deleted successfully.", status_code=status.HTTP_204_NO_CONTENT)
