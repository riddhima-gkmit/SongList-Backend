from rest_framework import serializers
from music.models.genre_models import Genre


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for Genre model."""
    song_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Genre
        fields = ['id', 'name', 'description', 'song_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_song_count(self, obj):
        """Return count of songs with this genre."""
        return obj.songs.count()
