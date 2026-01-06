from django.db import models
from django.utils import timezone

from common.models import BaseModel
from users.models import User
from common.constants import NAME_MAX_LENGTH 


class Playlist(BaseModel):
    """
    User playlist.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists",)
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    description = models.TextField(blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "playlists"
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
