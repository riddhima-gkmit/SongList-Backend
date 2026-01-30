"""
Views for Song Request CRUD and review operations.
"""
import uuid
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status

from common.enums import UserRole
from common.responses import success_response, error_response
from common.cache_utils import invalidate_tenant_songs_list_cache
from common.permissions import IsAdmin, IsTenantUser
from common.pagination import DefaultPagination
from music.models import SongRequest, RequestStatus, Song
from music.serializers import (
    SongRequestCreateSerializer,
    SongRequestListSerializer,
    SongRequestDetailSerializer,
    SongRequestReviewSerializer,
    SongRequestFulfillSerializer,
)
from users.models import User


class SongRequestListCreateAPIView(APIView):
    """List song requests or create a new request (LISTENER)."""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request):
        """List song requests (filtered by role)."""
        try:
            # Admin sees all requests in their tenant, users see only their own
            if request.user.is_admin:
                requests = SongRequest.objects.filter(tenant=request.user.tenant).order_by('-created_at')
                # Allow status filtering
                status_filter = request.query_params.get('status')
                if status_filter:
                    requests = requests.filter(status=status_filter)
            else:
                requests = SongRequest.objects.filter(requester=request.user).order_by('-created_at')
            
            # Apply pagination
            paginator = DefaultPagination()
            page = paginator.paginate_queryset(requests, request)
            serializer = SongRequestListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        """Create a new song request."""
        try:
            tenant = request.user.tenant
            if not tenant.is_active:
                return error_response("Tenant not found.", status_code=http_status.HTTP_400_BAD_REQUEST)

            if SongRequest.objects.filter(song_title=request.data.get('song_title'), tenant=tenant).exists():
                return error_response("Song request already exists.", status_code=http_status.HTTP_400_BAD_REQUEST)
            target_user = request.user
            
            if request.user.role == UserRole.ADMIN:
                user_id = request.data.get('user_id')
                if not user_id:
                    return error_response(
                        "user_id is required to create song request for another user.",
                        status_code=http_status.HTTP_400_BAD_REQUEST
                    )
                if uuid.UUID(user_id) == request.user.id:
                    return error_response(
                        "You cannot create song request for yourself.",
                        status_code=http_status.HTTP_400_BAD_REQUEST
                    )
                target_user = User.objects.filter(id=user_id, tenant_id=tenant.id).first()
                if not target_user:
                    return error_response(
                        "User not found.",
                        status_code=http_status.HTTP_400_BAD_REQUEST
                    )
                elif target_user.role == UserRole.ADMIN:
                    return error_response(
                        "You cannot create song request for another admin.",
                        status_code=http_status.HTTP_400_BAD_REQUEST
                    )
            
            serializer = SongRequestCreateSerializer(
                data=request.data,
                context={'request': request, 'tenant': tenant, 'requester': target_user}
            )
            serializer.is_valid(raise_exception=True)
            song_request = serializer.save()
            
            detail_serializer = SongRequestDetailSerializer(song_request)
            return success_response(
                message="Song request created successfully.",
                data=detail_serializer.data,
                status_code=http_status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)


class SongRequestDetailAPIView(APIView):
    """Retrieve, update, or delete a specific song request."""
    permission_classes = [IsAuthenticated, IsTenantUser]

    def get(self, request, request_id):
        """Get song request details."""
        try:
            song_request = SongRequest.objects.get(id=request_id)
            
            # LISTENER can only view their own requests, ADMIN can view all in tenant
            if not request.user.is_admin and song_request.requester != request.user:
                return error_response("Permission denied.", status_code=http_status.HTTP_403_FORBIDDEN)
            
            serializer = SongRequestDetailSerializer(song_request)
            return success_response(message="Song request retrieved.", data=serializer.data)
        except SongRequest.DoesNotExist:
            return error_response("Song request not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, request_id):
        """Update song request (own requests or admin)."""
        try:
            song_request = SongRequest.objects.get(id=request_id)
            
            # Permission check: LISTENER can update own, ADMIN can update any in tenant
            if not request.user.is_admin and song_request.requester != request.user:
                return error_response("Permission denied.", status_code=http_status.HTTP_403_FORBIDDEN)
            
            # Cannot update if already reviewed
            if song_request.status != RequestStatus.PENDING:
                return error_response("Cannot update reviewed requests.", status_code=http_status.HTTP_400_BAD_REQUEST)
            
            # Update the request
            serializer = SongRequestDetailSerializer(song_request, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return success_response(message="Song request updated successfully.")
        except SongRequest.DoesNotExist:
            return error_response("Song request not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, request_id):
        """Delete song request (own requests or admin)."""
        try:
            song_request = SongRequest.objects.get(id=request_id)
            
            # Permission check: LISTENER can delete own, ADMIN can delete any in tenant
            if not request.user.is_admin and song_request.requester != request.user:
                return error_response("Permission denied.", status_code=http_status.HTTP_403_FORBIDDEN)
            
            song_request.delete(deleted_by=request.user)  # Soft delete
            return success_response(message="Song request deleted successfully.", status_code=http_status.HTTP_204_NO_CONTENT)
        except SongRequest.DoesNotExist:
            return error_response("Song request not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSongRequestReviewAPIView(APIView):
    """Admin endpoint to approve/reject song requests."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, request_id):
        """Approve or reject a song request."""
        try:
            song_request = SongRequest.objects.get(id=request_id)
            
            serializer = SongRequestReviewSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            action = serializer.validated_data['action']
            
            if action == 'approve':
                song_request.approve(request.user)
                return success_response(message="Song request approved.")
            elif action == 'reject':
                reason = serializer.validated_data['rejection_reason']
                song_request.reject(request.user, reason)
                return success_response(message="Song request rejected.")
        except SongRequest.DoesNotExist:
            return error_response("Song request not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)


class AdminSongRequestFulfillAPIView(APIView):
    """Admin endpoint to fulfill a song request by linking to a song."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, request_id):
        """Fulfill a song request with a song and auto-link to tenant if GLOBAL."""
        try:
            song_request = SongRequest.objects.get(id=request_id, status=RequestStatus.APPROVED)
            
            serializer = SongRequestFulfillSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            song = Song.objects.get(id=serializer.validated_data['song_id'])
            
            # Add song to TenantSong table (for both GLOBAL and TENANT songs)
            from music.models.tenant_song_models import TenantSong
            
            # Check if TenantSong link already exists (including soft-deleted)
            existing_tenant_song = TenantSong.objects.filter(
                tenant=request.user.tenant,
                song=song
            ).first()
            
            if existing_tenant_song:
                # If soft-deleted, restore it
                if existing_tenant_song.deleted_at:
                    existing_tenant_song.deleted_at = None
                    existing_tenant_song.deleted_by = None
                    existing_tenant_song.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])
                    message = "Song request fulfilled and song restored in tenant successfully."
                else:
                    message = "Song request fulfilled successfully. Song already linked to tenant."
            else:
                # Create new tenant-song link
                TenantSong.objects.create(
                    tenant=request.user.tenant,
                    song=song
                )
                message = "Song request fulfilled and song added to tenant successfully."
            
            # Mark request as fulfilled
            song_request.fulfill(song)
            invalidate_tenant_songs_list_cache(str(request.user.tenant_id))
            return success_response(message=message)
        except SongRequest.DoesNotExist:
            return error_response("Approved song request not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Song.DoesNotExist:
            return error_response("Song not found.", status_code=http_status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return error_response(str(e), status_code=http_status.HTTP_400_BAD_REQUEST)
