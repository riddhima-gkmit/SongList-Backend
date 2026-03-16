from django.db import models
from django.utils import timezone

from common.models import SoftDeleteModel
from .playlist_models import Playlist
from .tenant_song_models import TenantSong


class PlaylistSong(SoftDeleteModel):
    """
    Join table between Playlist and TenantSong.
    """

    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="playlist_songs",)
    tenant_song = models.ForeignKey(TenantSong, on_delete=models.CASCADE, related_name="playlist_songs",)

    class Meta:
        db_table = "playlist_songs"
        unique_together = ("playlist", "tenant_song")
