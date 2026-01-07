from rest_framework import serializers
from music.models.playlist import Playlist
from music.models.playlist_song import PlaylistSong
from music.models.song import Song
from common.enums import SongStatus


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
        """Ensure playlist name is not empty after stripping whitespace."""
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Playlist name cannot be empty.")

        return value


class PlaylistSongAddSerializer(serializers.Serializer):
    """
    Serializer to add a song to a playlist.
    """
    song_id = serializers.UUIDField()

    def validate(self, attrs):
        """
        Validate that the song can be added to the playlist.
        
        Checks:
        - Song exists
        - Song is approved
        - Song is not already in playlist
        """
        playlist = self.context["playlist"]
        song_id = attrs["song_id"]

        # Check if song exists
        try:
            song = Song.objects.get(id=song_id)
        except Song.DoesNotExist:
            raise serializers.ValidationError("Song does not exist.")

        # Only approved songs can be added
        if song.status != SongStatus.APPROVED:
            raise serializers.ValidationError("Only approved songs can be added.")

        # Prevent duplicate songs in playlist
        if PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
            raise serializers.ValidationError("Song already exists in playlist.")

        attrs["song"] = song
        return attrs
