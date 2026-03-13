from django.contrib import admin

from music.models.genre_models import Genre
from music.models.song_models import Song
from music.models.playlist_models import Playlist
from music.models.playlist_song_models import PlaylistSong
from music.models.tenant_song_models import TenantSong
admin.site.register(Genre)
admin.site.register(Song)
admin.site.register(Playlist)
admin.site.register(PlaylistSong)
admin.site.register(TenantSong)
