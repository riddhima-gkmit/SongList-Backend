from rest_framework import serializers
from common.enums import SongStatus


class SongReviewSerializer(serializers.Serializer):
    """
    Serializer for admin song approval / rejection.
    """

    status = serializers.ChoiceField(
        choices=[SongStatus.APPROVED, SongStatus.REJECTED]
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        status = attrs.get("status")
        reason = attrs.get("rejection_reason", "")

        # Rejection reason is required when rejecting
        if status == SongStatus.REJECTED:
            if not reason or not reason.strip():
                raise serializers.ValidationError(
                    {"rejection_reason": "Rejection reason is required when rejecting a song."}
                )
            attrs["rejection_reason"] = reason.strip()
        else:
            # Clear rejection reason on approval
            attrs["rejection_reason"] = None

        return attrs
