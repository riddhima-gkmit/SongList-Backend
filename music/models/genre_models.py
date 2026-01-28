from django.db import models
from common.models import BaseModel


class Genre(BaseModel):
    """Genre model."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "genres"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        """Delete genre if no songs linked."""
        # Check for songs that are not soft-deleted
        active_songs = self.songs.filter(deleted_at__isnull=True)
        if active_songs.exists():
            count = active_songs.count()
            raise ValueError(
                f"Cannot delete genre as it is linked to {count} song(s). "
                "Please remove or delete all linked songs first."
            )
        super().delete(*args, **kwargs)
