from django.urls import path
from music.views.song import SongAPIView, SongDetailAPIView
from music.views.playlist import PlaylistAPIView, PlaylistDetailAPIView, PlaylistSongAPIView
from music.views.review import SongReviewAPIView

urlpatterns = [
    path("songs/", SongAPIView.as_view()),
    path("songs/<uuid:id>/", SongDetailAPIView.as_view()),
    path("songs/<uuid:id>/review/", SongReviewAPIView.as_view()),

    path("playlists", PlaylistAPIView.as_view()),
    path("playlists/<uuid:id>/", PlaylistDetailAPIView.as_view()),
    path("playlists/<uuid:id>/songs/", PlaylistSongAPIView.as_view()),
    path("playlists/<uuid:playlist_id>/songs/<uuid:song_id>/", PlaylistSongAPIView.as_view()),
]
