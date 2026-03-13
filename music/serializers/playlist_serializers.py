from rest_framework import serializers
from music.models.playlist_models import Playlist
from music.models.playlist_song_models import PlaylistSong
from music.models.tenant_song_models import TenantSong


class PlaylistSerializer(serializers.ModelSerializer):
    """
    Serializer for Playlist CRUD operations.
    """

    class Meta:
        model = Playlist
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Ensure playlist name is not empty and unique per user (excluding soft-deleted)."""
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Playlist name cannot be empty.")

        # Get target user from context (for admin creating playlist for another user)
        target_user = self.context.get('target_user')
        if not target_user:
            # Fallback to request.user if target_user not provided
            request = self.context.get('request')
            if request and request.user:
                target_user = request.user
            else:
                return value  # Skip validation if no user context
        
        # Check for existing playlist with same name for target user (excluding soft-deleted)
        existing_playlist = Playlist.objects.filter(
            user=target_user,
            name__iexact=value,
            deleted_at__isnull=True
        )
        
        # Exclude current instance if updating
        if self.instance:
            existing_playlist = existing_playlist.exclude(id=self.instance.id)
        
        if existing_playlist.exists():
            raise serializers.ValidationError(
                "A playlist with this name already exists for this user. Please choose a different name."
            )

        return value


class PlaylistSongAddSerializer(serializers.Serializer):
    """
    Serializer to add a tenant song to a playlist.
    """
    tenant_song_id = serializers.UUIDField()

    def validate(self, attrs):
        """
        Validate that the tenant song can be added to the playlist.
        
        Checks:
        - TenantSong exists
        - TenantSong is active and not deleted
        - TenantSong is not already in playlist
        """
        playlist = self.context["playlist"]
        request = self.context["request"]
        tenant_song_id = attrs["tenant_song_id"]

        # Check if tenant song exists and belongs to user's tenant
        try:
            tenant_song = TenantSong.objects.get(
                id=tenant_song_id,
                tenant=request.user.tenant,
                deleted_at__isnull=True
            )
        except TenantSong.DoesNotExist:
            raise serializers.ValidationError("Tenant song does not exist or is not available in your tenant.")

        # Prevent duplicate tenant songs in playlist (only check non-deleted)
        if PlaylistSong.objects.filter(playlist=playlist, tenant_song=tenant_song, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Song already exists in playlist.")

        attrs["tenant_song"] = tenant_song
        return attrs
