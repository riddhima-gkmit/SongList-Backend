from rest_framework import serializers
from music.models import SongRequest, Song


class SongRequestCreateSerializer(serializers.ModelSerializer):
    """Create song request."""
    
    class Meta:
        model = SongRequest
        fields = [
            'song_title',
            'artist_name',
            'album_name',
            'additional_notes',
        ]
        
    def create(self, validated_data):
        """Create song request."""
        user = self.context.get('requester')
        tenant = self.context.get('tenant')  # Set by view
        
        return SongRequest.objects.create(  
            requester=user,
            tenant=tenant,
            **validated_data
        )


class SongRequestListSerializer(serializers.ModelSerializer):
    """List song requests."""
    requester_email = serializers.EmailField(source='requester.email', read_only=True)
    requester_name = serializers.CharField(source='requester.username', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SongRequest
        fields = [
            'id',
            'song_title',
            'artist_name',
            'album_name',
            'status',
            'status_display',
            'requester_email',
            'requester_name',
            'reviewed_by_email',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SongRequestDetailSerializer(serializers.ModelSerializer):
    """Song request detail."""
    requester_email = serializers.EmailField(source='requester.email', read_only=True)
    requester_name = serializers.CharField(source='requester.username', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    fulfilled_song_title = serializers.CharField(source='fulfilled_song.title', read_only=True, allow_null=True)
    
    class Meta:
        model = SongRequest
        fields = [
            'id',
            'song_title',
            'artist_name',
            'album_name',
            'additional_notes',
            'status',
            'status_display',
            'requester_email',
            'requester_name',
            'reviewed_by_email',
            'reviewed_at',
            'rejection_reason',
            'fulfilled_song_title',
            'fulfilled_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SongRequestReviewSerializer(serializers.Serializer):
    """Review song request."""
    action = serializers.ChoiceField(choices=['approve', 'reject'], required=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate rejection reason."""
        if attrs.get('action') == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting a request.'
            })
        return attrs


class SongRequestFulfillSerializer(serializers.Serializer):
    """Fulfill song request."""
    song_id = serializers.UUIDField(required=True)
    
    def validate_song_id(self, value):
        """Check song exists."""
        try:
            Song.objects.get(id=value)
        except Song.DoesNotExist:
            raise serializers.ValidationError("Song with this ID does not exist.")
        return value
