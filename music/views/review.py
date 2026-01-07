from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404

from music.models.song import Song
from music.serializers.review import SongReviewSerializer
from common.permissions import IsAdmin
from common.enums import SongStatus


class SongReviewAPIView(APIView):
    """
    Admin-only API to approve or reject songs (new or updated).
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, id):
        """
        Approve or reject a pending song.
        """
        try:
            # Only pending songs can be reviewed
            song = get_object_or_404(
                Song,
                id=id,
                status=SongStatus.PENDING,
            )

            serializer = SongReviewSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Update song status and save
            song.status = serializer.validated_data["status"]
            song.rejection_reason = serializer.validated_data.get("rejection_reason")
            song.save(update_fields=["status", "rejection_reason"])

            return Response(
                {"message": f"Song {song.status.lower()} successfully"},
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Http404:
            return Response(
                {"error": "Song not found or not pending review."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "Failed to review song.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
