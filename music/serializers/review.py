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
        allow_null=True,
    )

    def validate(self, attrs):
        status = attrs.get("status")
        reason = attrs.get("rejection_reason")

        # Rejection reason is required when rejecting
        if status == SongStatus.REJECTED:
            if not reason or (isinstance(reason, str) and not reason.strip()):
                raise serializers.ValidationError(
                    {"rejection_reason": "Rejection reason is required when rejecting a song."}
                )
            attrs["rejection_reason"] = reason.strip() if isinstance(reason, str) else reason
        else:
            # Clear rejection reason on approval (use empty string, not None)
            attrs["rejection_reason"] = ""

        return attrs
