from rest_framework import serializers
from music.models.tenant_song_models import TenantSong
from music.models.song_models import Song


class TenantSongSerializer(serializers.ModelSerializer):
    """Serializer for TenantSong with song details."""
    title = serializers.CharField(source='song.title')
    genre = serializers.CharField(source='song.genre.name')
    artist = serializers.CharField(source='song.artist')
    album = serializers.CharField(source='song.album')
    duration = serializers.IntegerField(source='song.duration')
    release_year = serializers.IntegerField(source='song.release_year')
    
    class Meta:
        model = TenantSong
        fields = ['id', 'title', 'genre', 'artist', 'album', 'duration', 'release_year', 'created_at', 'updated_at']
        read_only_fields = ['id', 'title', 'genre', 'artist', 'album', 'duration', 'release_year', 'created_at', 'updated_at']


class TenantSongCreateSerializer(serializers.Serializer):
    """Serializer for creating tenant-song link."""
    song_id = serializers.UUIDField()
    
    def validate_song_id(self, value):
        """Validate that song exists and is GLOBAL."""
        try:
            song = Song.objects.get(id=value, visibility='GLOBAL')
            return song
        except Song.DoesNotExist:
            raise serializers.ValidationError("GLOBAL song not found with this ID.")
    
    def create(self, validated_data):
        """Create tenant-song link."""
        tenant = self.context['tenant']
        song = validated_data['song_id']
        
        # Check if already linked
        if TenantSong.objects.filter(tenant=tenant, song=song).exists():
            raise serializers.ValidationError("Song already linked to this tenant.")
        
        tenant_song = TenantSong.objects.create(tenant=tenant, song=song)
        return tenant_song
