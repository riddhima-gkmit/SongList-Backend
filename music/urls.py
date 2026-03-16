from django.urls import path
from music.views.song_views import SongAPIView, SongDetailAPIView
from music.views.playlist_views import PlaylistAPIView, PlaylistDetailAPIView, PlaylistSongAPIView
from music.views.song_request_views import (
    SongRequestListCreateAPIView,
    SongRequestDetailAPIView,
    AdminSongRequestReviewAPIView,
    AdminSongRequestFulfillAPIView,
)
from music.views.bulk_song_views import BulkAddTenantSongsAPIView, BulkDeleteTenantSongsAPIView
from music.views.genre_views import GenreListCreateAPIView, GenreDetailAPIView
from music.views.tenant_song_views import (
    TenantSongListCreateAPIView,
    TenantSongDetailAPIView,
)

urlpatterns = [
    # Genres
    path("genres/", GenreListCreateAPIView.as_view(), name='genre_list'),
    path("genres/<uuid:id>/", GenreDetailAPIView.as_view(), name='genre_detail'),
    
    # Tenant-Song Links (Admin only)
    path("tenant/songs/", TenantSongListCreateAPIView.as_view(), name='tenant_song_list'),
    path("tenant/songs/bulk-delete/", BulkDeleteTenantSongsAPIView.as_view(), name='tenant_song_bulk_delete'),
    path("tenant/songs/<uuid:id>/", TenantSongDetailAPIView.as_view(), name='tenant_song_detail'),
    
    # Songs
    path("songs/", SongAPIView.as_view(), name='song_list'),
    path("songs/bulk-add/", BulkAddTenantSongsAPIView.as_view(), name='bulk_song_add'),  # Admin only
    path("songs/<uuid:id>/", SongDetailAPIView.as_view(), name='song_detail'),

    # Playlists
    path("playlists/", PlaylistAPIView.as_view(), name='playlist_list'),
    path("playlists/<uuid:id>/", PlaylistDetailAPIView.as_view(), name='playlist_detail'),
    path("playlists/<uuid:id>/songs/", PlaylistSongAPIView.as_view(), name='playlist_songs'),
    path("playlists/<uuid:playlist_id>/songs/<uuid:song_id>/", PlaylistSongAPIView.as_view(), name='playlist_song_detail'),
    
    # Song Requests - Consolidated (role-based access via permissions)
    path("song-requests/", SongRequestListCreateAPIView.as_view(), name='song_request_list_create'),  # Users + Admins (filtered)
    path("song-requests/<uuid:request_id>/", SongRequestDetailAPIView.as_view(), name='song_request_detail'),
    path("song-requests/<uuid:request_id>/review/", AdminSongRequestReviewAPIView.as_view(), name='song_request_review'),  # Admin only
    path("song-requests/<uuid:request_id>/fulfill/", AdminSongRequestFulfillAPIView.as_view(), name='song_request_fulfill'),  # Admin only
]
