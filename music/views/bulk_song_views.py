from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from common.responses import success_response, error_response
from common.permissions import IsAdmin
from music.models.tenant_song_models import TenantSong
from music.models.song_models  import Song
from music.serializers.bulk_song_serializers import BulkAddTenantSongsSerializer, BulkDeleteTenantSongsSerializer
from music.models.playlist_song_models import PlaylistSong
from django.utils import timezone


class BulkAddTenantSongsAPIView(APIView):
    """Bulk add songs to tenant."""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Add songs by ids, genres, or artists."""
        try:
            tenant = request.user.tenant
            if not tenant:
                return error_response(
                    "No tenant associated with user.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = BulkAddTenantSongsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            song_ids = set()
            
            # Collect song IDs from song_ids
            if data.get('song_ids'):
                song_ids.update(data['song_ids'])
            
            # Collect song IDs from genres
            if data.get('genre_ids'):
                genre_songs = Song.objects.filter(
                    genre_id__in=data['genre_ids'],
                    deleted_at__isnull=True,
                ).values_list('id', flat=True)
                song_ids.update(genre_songs)
            
            # Collect song IDs from artists
            if data.get('artists'):
                artist_songs = Song.objects.filter(
                    artist__in=data['artists'],
                    deleted_at__isnull=True
                ).values_list('id', flat=True)
                song_ids.update(artist_songs)
            
            if not song_ids:
                return error_response(
                    "No songs found matching the provided criteria.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            song_ids = list(song_ids)
            
            # Get existing tenant_songs (including soft-deleted)
            existing_tenant_songs = TenantSong.objects.all_with_deleted().filter(
                tenant=tenant,
                song_id__in=song_ids
            )
            
            # Count existing active tenant_songs before operations
            existing_active_count = TenantSong.objects.filter(
                tenant=tenant,
                song_id__in=song_ids,
                deleted_at__isnull=True,
                is_active=True
            ).count()
            
            # Separate into existing active, existing soft-deleted, and new
            existing_active_ids = set(
                existing_tenant_songs.filter(deleted_at__isnull=True)
                .values_list('song_id', flat=True)
            )
            existing_deleted = existing_tenant_songs.filter(deleted_at__isnull=False)
            new_song_ids = [sid for sid in song_ids if sid not in existing_active_ids]
            
            # Restore soft-deleted tenant_songs
            if existing_deleted.exists():
                existing_deleted.update(
                    deleted_at=None,
                    deleted_by=None,
                    is_active=True
                )
            
            # Create new tenant_songs for songs not yet linked
            if new_song_ids:
                tenant_songs_to_create = [
                    TenantSong(tenant=tenant, song_id=song_id, is_active=True)
                    for song_id in new_song_ids
                ]
                TenantSong.objects.bulk_create(tenant_songs_to_create, ignore_conflicts=True)
            
            # Count actual active tenant_songs after operations
            # This gives us the accurate count of what was actually added
            final_active_count = TenantSong.objects.filter(
                tenant=tenant,
                song_id__in=song_ids,
                deleted_at__isnull=True,
                is_active=True
            ).count()
            
            total_added = final_active_count - existing_active_count
            
            return success_response(
                message=f"Successfully added {total_added} song(s) to tenant.",
                data={'total_added_songs': total_added},
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



class BulkDeleteTenantSongsAPIView(APIView):
    """Bulk delete tenant-song links."""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Bulk delete tenant-song links."""
        try:
            serializer = BulkDeleteTenantSongsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            tenant_song_ids = serializer.validated_data['tenant_song_ids']
            
            tenant_songs = TenantSong.objects.filter(
                id__in=tenant_song_ids,
                tenant=request.user.tenant
            )
            
            deleted_count = tenant_songs.count()
            
            if deleted_count == 0:
                return error_response(
                    "No valid tenant-song links found to delete.",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            tenant_song_ids_to_process = list(tenant_songs.values_list('id', flat=True))
            
            tenant_songs.update(
                deleted_at=timezone.now(),
                deleted_by=request.user,
                updated_at=timezone.now()
            )
            
            PlaylistSong.objects.filter(
                tenant_song_id__in=tenant_song_ids_to_process,
                playlist__user__tenant=request.user.tenant,
                deleted_at__isnull=True
            ).update(
                deleted_at=timezone.now(),
                deleted_by=request.user,
                updated_at=timezone.now()
            )
            
            return success_response(
                message=f"Successfully deleted {deleted_count} tenant-song link(s).",
                data={"deleted_count": deleted_count}
            )
        except Exception as e:
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
