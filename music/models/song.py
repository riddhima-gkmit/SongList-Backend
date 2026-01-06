from django.db import models
from django.utils import timezone

from common.models import BaseModel
from common.enums import SongStatus
from users.models import User
from .genre import Genre
from common.constants import STATUS_MAX_LENGTH, NAME_MAX_LENGTH 


class Song(BaseModel):
    """
    Represents a song in the music library.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="songs",)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="songs",)

    title = models.CharField(max_length=NAME_MAX_LENGTH )
    artist = models.CharField(max_length=NAME_MAX_LENGTH )
    album = models.CharField(max_length=NAME_MAX_LENGTH , blank=True)
    duration = models.PositiveSmallIntegerField()
    release_year = models.PositiveSmallIntegerField()

    status = models.CharField(
        max_length=STATUS_MAX_LENGTH,
        choices=SongStatus.choices,
        default=SongStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "songs"
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False):
        """Soft delete song"""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
