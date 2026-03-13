from rest_framework import serializers
from django.utils import timezone
from music.models.song_models import Song


class SongSerializer(serializers.ModelSerializer):
    """
    Serializer for Song creation and retrieval.
    """
    class Meta:
        model = Song
        fields = [
            "id",
            "user",
            "genre",
            "title",
            "artist",
            "album",
            "tenant",
            "duration",
            "visibility",
            "release_year",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]
    
    # Field validations
    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Song title cannot be empty.")
        return value

    def validate_artist(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Artist name cannot be empty.")
        return value

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Duration must be greater than 0 seconds."
            )
        return value

    def validate_release_year(self, value):
        from common.constants import MIN_RELEASE_YEAR
        current_year = timezone.now().year
        if value > current_year:
            raise serializers.ValidationError(
                f"Release year cannot be in the future. (Current year: {current_year})"
            )
        if value < MIN_RELEASE_YEAR:
            raise serializers.ValidationError(
                f"Release year cannot be less than {MIN_RELEASE_YEAR}. (Current year: {current_year})"
            )
        return value

    def create(self, validated_data):
        song = Song.objects.filter(title__iexact=validated_data['title'])
        if song.exists():
            raise serializers.ValidationError(
               {"title": "Song with this title already exists."}
            )

        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
