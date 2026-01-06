from django.db import models

from common.models import BaseModel
from .playlist import Playlist
from .song import Song


class PlaylistSong(BaseModel):
    """
    Join table between Playlist and Song.
    """

    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="playlist_songs",)
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="song_playlists",)

    class Meta:
        db_table = "playlist_songs"
        unique_together = ("playlist", "song")
