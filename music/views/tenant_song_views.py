"""Tenant-Song link views."""
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.responses import success_response, error_response
from common.pagination import DefaultPagination
from common.enums import UserRole
from music.models.tenant_song_models import TenantSong
from music.models.playlist_song_models import PlaylistSong
from music.serializers.tenant_song_serializers import TenantSongSerializer, TenantSongCreateSerializer
from music.filters import SongQueryFilter


class TenantSongListCreateAPIView(APIView):
    """List/link songs to tenant."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List tenant songs."""
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                return error_response("Super Admin cannot access tenant songs.", status_code=status.HTTP_403_FORBIDDEN)
            
            if request.user.role == UserRole.ADMIN:
                links = TenantSong.objects.filter(tenant=request.user.tenant, song__deleted_at__isnull=True).select_related('song')
            else:
                links = TenantSong.objects.filter(
                    tenant=request.user.tenant,
                    deleted_at__isnull=True,
                    song__deleted_at__isnull=True,
                ).select_related('song')
            
            # Apply filters (title, genre, artist, album)
            links = SongQueryFilter(links, request.query_params).apply()
            
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(links, request)
            
            serializer = TenantSongSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Link song to tenant."""
        try:
            if request.user.role != UserRole.ADMIN:
                return error_response("Only admins can link songs to tenant.", status_code=status.HTTP_403_FORBIDDEN)
            
            serializer = TenantSongCreateSerializer(
                data=request.data,
                context={'tenant': request.user.tenant}
            )
            serializer.is_valid(raise_exception=True)
            tenant_song = serializer.save()
            
            return success_response(
                message="Song linked to tenant successfully.",
                data=TenantSongSerializer(tenant_song).data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)


class TenantSongDetailAPIView(APIView):
    """Get/unlink tenant-song link."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """Get tenant-song link."""
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                return error_response("Super Admin cannot access tenant songs.", status_code=status.HTTP_403_FORBIDDEN)
            
            if request.user.role == UserRole.ADMIN:
                link = TenantSong.objects.get(
                    id=id,
                    tenant=request.user.tenant
                )
            else:
                link = TenantSong.objects.get(
                    id=id,
                    tenant=request.user.tenant,
                    deleted_at__isnull=True
                )
            serializer = TenantSongSerializer(link)
            return success_response(message="Tenant-song link retrieved.", data=serializer.data)
        except Exception as e:
            return error_response("Tenant-song link not found.", status_code=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, id):
        """Unlink song from tenant."""
        try:
            if request.user.role != UserRole.ADMIN:
                return error_response("Only admins can unlink songs from tenant.", status_code=status.HTTP_403_FORBIDDEN)
            
            link = TenantSong.objects.get(
                id=id,
                tenant=request.user.tenant
            )
            
            link.delete(deleted_by=request.user)
            
            PlaylistSong.objects.filter(
                tenant_song=link,
                playlist__user__tenant=request.user.tenant,
                deleted_at__isnull=True
            ).update(
                deleted_at=timezone.now(),
                deleted_by=request.user
            )
            
            return success_response(message="Song unlinked from tenant successfully.", status_code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return error_response("Tenant-song link not found.", status_code=status.HTTP_404_NOT_FOUND)





