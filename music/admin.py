from django.contrib import admin

from music.models.genre import Genre
from music.models.song import Song
from music.models.playlist import Playlist
from music.models.playlist_song import PlaylistSong

admin.site.register(Genre)
admin.site.register(Song)
admin.site.register(Playlist)
admin.site.register(PlaylistSong)
