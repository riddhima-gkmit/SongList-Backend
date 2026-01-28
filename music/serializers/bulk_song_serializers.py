from rest_framework import serializers
from music.models.song_models import Song
from music.models.genre_models import Genre


class BulkAddTenantSongsSerializer(serializers.Serializer):
    """Bulk add songs to tenant."""
    song_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    genre_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    artists = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    
    def validate(self, data):
        """Check at least one field is provided."""
        if not data.get('song_ids') and not data.get('genre_ids') and not data.get('artists'):
            raise serializers.ValidationError("At least one of song_ids, genre_ids, or artists must be provided.")
        return data
    
    def validate_song_ids(self, value):
        """Check songs exist."""
        if not value:
            return value
        existing = Song.objects.filter(id__in=value).values_list('id', flat=True)
        missing = set(value) - set(existing)
        if missing:
            raise serializers.ValidationError(f"Songs not found: {', '.join(str(id) for id in missing)}")
        return value
    
    def validate_genre_ids(self, value):
        """Check genres exist."""
        if not value:
            return value
        existing = Genre.objects.filter(id__in=value).values_list('id', flat=True)
        missing = set(value) - set(existing)
        if missing:
            raise serializers.ValidationError(f"Genres not found: {', '.join(str(id) for id in missing)}")
        return value

class BulkDeleteTenantSongsSerializer(serializers.Serializer):
    """Bulk delete serializer."""
    tenant_song_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )