from django.db import models

from common.models import SoftDeleteModel
from common.managers import SoftDeleteManager
from users.models import User


class Playlist(SoftDeleteModel):
    """User playlist."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    objects = SoftDeleteManager()

    class Meta:
        db_table = "playlists"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_playlist_name_per_user',
                condition=models.Q(deleted_at__isnull=True)
            ),
        ]
    
    def __str__(self):
        return self.name
