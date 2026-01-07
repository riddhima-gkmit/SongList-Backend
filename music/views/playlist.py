from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from music.models.playlist import Playlist
from music.models.playlist_song import PlaylistSong
from music.serializers.playlist import (
    PlaylistSerializer,
    PlaylistSongAddSerializer,
)
from common.pagination import DefaultPagination
from common.permissions import IsOwnerOrAdmin

class PlaylistAPIView(APIView):
    """
    List playlists.
    
    - User: only their own playlists
    - Admin: all playlists
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List playlists. Admin sees all, users see only their own."""
        try:
            queryset = Playlist.objects.all()

            # Users can only see their own playlists
            if not request.user.is_admin:
                queryset = queryset.filter(user=request.user)

            # Return paginated results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(queryset, request)

            serializer = PlaylistSerializer(page, many=True)

            return paginator.get_paginated_response(serializer.data)

        except Exception:
            return Response(
                {"error": "Failed to fetch playlists."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        Create a new playlist.
        """
        try:
            # Admins cannot create playlists
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot create playlists."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = PlaylistSerializer(
                data=request.data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
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
            playlist = get_object_or_404(Playlist, id=id)
            self.check_object_permissions(request, playlist)

            serializer = PlaylistSerializer(playlist)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
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
        """Update a playlist (partial update). Admins cannot update."""
        try:
            # Admins are not allowed to update playlists
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot update playlists."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            playlist = get_object_or_404(Playlist, id=id)
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

        except Http404:
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
            playlist = get_object_or_404(Playlist, id=id)
            self.check_object_permissions(request, playlist)

            playlist.delete()  # Soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Http404:
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
    
    Only playlist owners can add/remove songs. Admins cannot.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, id):
        """Add an approved song to playlist. Admins cannot add songs."""
        try:
            # Admins are not allowed to add songs to playlists
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot add songs to playlists."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            playlist = get_object_or_404(Playlist, id=id)
            self.check_object_permissions(request, playlist)

            serializer = PlaylistSongAddSerializer(
                data=request.data,
                context={"playlist": playlist, "request": request},
            )
            serializer.is_valid(raise_exception=True)

            PlaylistSong.objects.create(
                playlist=playlist,
                song=serializer.validated_data["song"],
            )

            return Response(
                {"message": "Song added to playlist"},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Http404:
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
        """Remove a song from playlist. Admins cannot remove songs."""
        try:
            # Admins are not allowed to remove songs from playlists
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot remove songs from playlists."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            playlist = get_object_or_404(Playlist, id=playlist_id)
            self.check_object_permissions(request, playlist)

            playlist_song = get_object_or_404(
                PlaylistSong,
                playlist=playlist,
                song_id=song_id,
            )

            playlist_song.delete()  # soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Http404:
            return Response(
                {"error": "Playlist or song not found."},
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

 
