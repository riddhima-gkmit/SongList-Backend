from rest_framework import serializers
from django.utils import timezone
from music.models.song import Song
from common.enums import SongStatus


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
            "duration",
            "release_year",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "rejection_reason",
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
        current_year = timezone.now().year
        if value > current_year:
            raise serializers.ValidationError(
                f"Release year cannot be in the future. (Current year: {current_year})"
            )
        return value

    
    # Object-level validation
    def validate(self, attrs):
        """
        Prevent users from modifying approved songs directly.
        """
        instance = self.instance

        if instance and instance.status == SongStatus.APPROVED:
            raise serializers.ValidationError(
                "Approved songs cannot be modified without admin review."
            )

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["status"] = SongStatus.PENDING
        return super().create(validated_data)
