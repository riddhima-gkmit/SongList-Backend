from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsOwnerOrAdmin
from rest_framework.serializers import ValidationError

from music.models.song import Song
from music.serializers.song import SongSerializer
from music.filters import SongQueryFilter
from common.pagination import DefaultPagination
from common.enums import SongStatus


class SongAPIView(APIView):
    """
    List songs or submit a new song.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List songs with optional filtering by artist, genre, or album."""
        try:
            # Admins see all songs by default, but can filter by status
            if request.user.is_admin:
                queryset = Song.objects.all()
                # Allow admins to filter by status if provided
                requested_status = request.query_params.get('status', None)
                if requested_status:
                    queryset = queryset.filter(status__iexact=requested_status)
            else:
                # Default: Users see only APPROVED songs
                # Query param 'status' allows filtering.
                # Non-admins can only see their own PENDING/REJECTED songs.
                requested_status = request.query_params.get('status', SongStatus.APPROVED)
                if requested_status:
                    # Case-insensitive match for convenience
                    if requested_status.upper() == SongStatus.APPROVED:
                        queryset = Song.objects.filter(status=SongStatus.APPROVED)
                    else:
                        # For any other status (Pending/Rejected), restrict to own songs
                        # This prevents users from seeing other users' pending requests
                        queryset = Song.objects.filter(
                            status__iexact=requested_status,
                            user=request.user
                        )

            # Apply query filters
            queryset = SongQueryFilter(queryset, request.query_params).apply()

            # Return paginated results
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(queryset, request)

            serializer = SongSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception:
            return Response(
                {"error": "Failed to fetch songs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Create a new song request (starts in PENDING status)."""
        try:
            # Admins cannot create song requests
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot create song requests."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            title = request.data.get('title', None)
            if not title:
                return Response(
                    {"error": "title is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Check if a song with this title already exists
            request_exists = Song.objects.filter(title__iexact=title).first()
            if request_exists:
                return Response(
                    {"error": "Request already exists. Wait for approval to add this song."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            serializer = SongSerializer(
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            return Response(
                {"error": "Failed to create song."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SongDetailAPIView(APIView):
    """
    Retrieve, update, or delete a single song.

    Access:
    - View: All authenticated users (Approved only for non-admins)
    - Update: Owner only (Admin is blocked)
    - Delete: Owner or Admin
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """Retrieve a single song by ID."""
        try:
            song = get_object_or_404(Song, id=id)

            # Restrict visibility for non-admins
            if not request.user.is_admin and song.status != SongStatus.APPROVED:
                 # Allow owners to see their own pending/rejected songs
                 if song.user != request.user:
                     return Response(
                        {"error": "Song not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            serializer = SongSerializer(song)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Http404:
            return Response(
                {"error": "Song not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            return Response(
                {"error": "Failed to retrieve song."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, id):
        """Update a song (partial update)."""
        try:
            # Admins cannot update songs
            if request.user.is_admin:
                return Response(
                    {"error": "Admins cannot update songs."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            song = get_object_or_404(Song, id=id)
            
            # Only Owner can update
            if song.user != request.user:
                return Response(
                    {"error": "You do not have permission to update this song."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = SongSerializer(song, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                {"message": "Song updated successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Http404:
            return Response(
                {"error": "Song not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            return Response(
                {"error": "Failed to update song."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, id):
        """Soft delete a song."""
        try:
            song = get_object_or_404(Song, id=id)

            # Owner or Admin can delete
            if not request.user.is_admin and song.user != request.user:
                return Response(
                    {"error": "You do not have permission to delete this song."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            song.delete()  # Soft delete
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Http404:
            return Response(
                {"error": "Song not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            return Response(
                {"error": "Failed to delete song."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
