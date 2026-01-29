import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.exceptions import PermissionDenied

from music.models.playlist_models import Playlist
from music.models.playlist_song_models import PlaylistSong
from music.serializers.playlist_serializers import (
    PlaylistSerializer,
    PlaylistSongAddSerializer,
)
from common.pagination import DefaultPagination
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsOwnerOrAdmin
from common.enums import UserRole
from common.responses import error_response
from users.models import User
from music.serializers.song_serializers import SongSerializer

class PlaylistAPIView(APIView):
    """
    List playlists.
    
    - User: only their own playlists
    - Admin: all playlists
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List playlists. Admin sees all in their tenant, users see only their own."""
        try:
            if request.user.role == UserRole.SUPER_ADMIN:
                return error_response("Super Admins cannot see playlists.", status_code=status.HTTP_403_FORBIDDEN)
            
            if request.user.role == UserRole.ADMIN:
                # Admin sees all playlists in their tenant
                queryset = Playlist.objects.filter(user__tenant=request.user.tenant)
            else:
                # LISTENER sees only their own playlists
                queryset = Playlist.objects.filter(user=request.user)

            # Return paginated results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(queryset, request)

            serializer = PlaylistSerializer(page, many=True)

            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(
                {"error": "Failed to fetch playlists."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        Create a new playlist.
        - LISTENER: Creates playlist for themselves
        - ADMIN: Can create playlist for any user in their tenant (user_id required)
        """
        try:
            # Super Admins cannot create playlists
            if request.user.role == UserRole.SUPER_ADMIN:
                return error_response("Super Admins cannot see playlists.", status_code=status.HTTP_403_FORBIDDEN)
            
            # Determine target user for playlist creation
            target_user = request.user
            
            # If admin, check if user_id is provided to create playlist for another user
            if request.user.role == UserRole.ADMIN:
                user_id = request.data.get('user_id')
                target_user = User.objects.filter(id=user_id).first()
                if not target_user:
                    return error_response(
                        "user_id is required to create playlist for another user.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                elif uuid.UUID(user_id) == request.user.id:
                    return error_response(
                        "You cannot create playlist for yourself.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                elif target_user.role == UserRole.ADMIN:
                    return error_response(
                        "You cannot create playlist for another admin.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            serializer = PlaylistSerializer(
                data=request.data, context={"request": request, "target_user": target_user}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=target_user)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"error": "Failed to create playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PlaylistDetailAPIView(APIView):
    """
    Retrieve, update, or soft-delete a playlist.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id):
        """Retrieve a single playlist by ID."""
        try:
            playlist = Playlist.objects.get(id=id)
            self.check_object_permissions(request, playlist)

            serializer = PlaylistSerializer(playlist)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to access this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception:
            return Response(
                {"error": "Failed to retrieve playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, id):
        """Update a playlist (partial update). Owner and admin can update."""
        try:
            playlist = Playlist.objects.get(id=id)
            self.check_object_permissions(request, playlist)

            serializer = PlaylistSerializer(
                playlist,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "Playlist updated successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to update this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception:
            return Response(
                {"error": "Failed to update playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, id):
        """Soft delete a playlist."""
        try:
            playlist = Playlist.objects.get(id=id)
            self.check_object_permissions(request, playlist)

            playlist.delete()  # Soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to delete this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception:
            return Response(
                {"error": "Failed to delete playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class PlaylistSongAPIView(APIView):
    """
    Manage songs within a playlist.
    
    - GET: Retrieve all songs in playlist (owner or admin)
    - POST: Add song to playlist (owner only)
    - DELETE: Remove song from playlist (owner only)
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get(self, request, id):
        """Get all songs in a playlist with pagination."""
        try:
            playlist = Playlist.objects.get(id=id)
            self.check_object_permissions(request, playlist)
            
            # Get all playlist songs with related tenant_song and song data (exclude soft-deleted)
            playlist_songs = PlaylistSong.objects.filter(
                playlist=playlist,
                deleted_at__isnull=True
            ).select_related('tenant_song', 'tenant_song__song')
            
            # Paginate results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(playlist_songs, request)
            
            # Serialize song data from playlist songs
            songs = [ps.tenant_song.song for ps in page]
            serializer = SongSerializer(songs, many=True)
            
            return paginator.get_paginated_response(serializer.data)
            
        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to view this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve playlist songs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, id):
        """Add a song to playlist. Owner and admin can add songs."""
        try:
            playlist = Playlist.objects.get(id=id)
            self.check_object_permissions(request, playlist)

            serializer = PlaylistSongAddSerializer(
                data=request.data,
                context={"playlist": playlist, "request": request},
            )
            serializer.is_valid(raise_exception=True)

            tenant_song = serializer.validated_data["tenant_song"]
            
            # Check if PlaylistSong exists but is soft-deleted
            playlist_song = PlaylistSong.objects.filter(
                playlist=playlist,
                tenant_song=tenant_song
            ).first()
            
            if playlist_song and playlist_song.deleted_at:
                # Restore soft-deleted PlaylistSong
                playlist_song.deleted_at = None
                playlist_song.deleted_by = None
                playlist_song.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])
            elif not playlist_song:
                # Create new PlaylistSong
                PlaylistSong.objects.create(
                    playlist=playlist,
                    tenant_song=tenant_song,
                )

            return Response(
                {"message": "Song added to playlist"},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to add songs to this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception:
            return Response(
                {"error": "Failed to add song to playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        
    def delete(self, request, playlist_id, song_id):
        """Remove a song from playlist. Owner and admin can remove songs."""
        try:
            playlist = Playlist.objects.get(id=playlist_id)
            self.check_object_permissions(request, playlist)

            playlist_song = PlaylistSong.objects.get(
                playlist=playlist,
                tenant_song_id=song_id,
            )

            playlist_song.delete()  # soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Playlist.DoesNotExist:
            return Response(
                {"error": "Playlist not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PlaylistSong.DoesNotExist:
            return Response(
                {"error": "Song not found in playlist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                {"error": "You do not have permission to remove songs from this playlist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        except Exception:
            return Response(
                {"error": "Failed to remove song from playlist."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

 
