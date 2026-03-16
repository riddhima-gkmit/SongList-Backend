from django.db.models import Q


class SongQueryFilter:
    """
    Query-parameter filters for Song list endpoint.

    Supported query parameters:
    - search   : case-insensitive match on song title (legacy, use 'title' instead)
    - title    : case-insensitive match on song title
    - artist   : comma-separated list of artists (case-insensitive match)
    - genre    : comma-separated list of genre names (case-insensitive match)
    - album    : comma-separated list of albums (case-insensitive match)
    
    Works with both Song querysets and TenantSong querysets (filters through song relationship).
    Invalid values result in an empty queryset (fail-soft) or are ignored.
    """

    def __init__(self, queryset, params):
        self.qs = queryset
        self.params = params
        # Detect if we're filtering TenantSong (which has a 'song' FK) vs Song directly
        # Check by model name or by checking if 'song' field exists in the model
        model_name = queryset.model.__name__
        self.is_tenant_song = model_name == 'TenantSong'
        self.field_prefix = 'song__' if self.is_tenant_song else ''

    def apply(self):
        self.filter_title()
        self.filter_artist()
        self.filter_genre()
        self.filter_album()
        return self.qs

    def filter_title(self):
        # Filter by title
        value = self.params.get("title")
        if not value:
            return
        field_name = f"{self.field_prefix}title"
        self.qs = self.qs.filter(**{f"{field_name}__icontains": value.strip()})

    def filter_artist(self):
        # Filter by artist name (supports comma-separated values)
        value = self.params.get("artist")
        if not value:
            return
        values = self._parse_str_list(value)
        if not values:
            return
        field_name = f"{self.field_prefix}artist"
        q_objects = Q()
        for v in values:
            q_objects |= Q(**{f"{field_name}__icontains": v})
        self.qs = self.qs.filter(q_objects)

    def filter_genre(self):
        # Filter by genre name (related model, supports comma-separated values)
        value = self.params.get("genre")
        if not value:
            return
        values = self._parse_str_list(value)
        if not values:
            return
        field_name = f"{self.field_prefix}genre__name"
        q_objects = Q()
        for v in values:
            q_objects |= Q(**{f"{field_name}__icontains": v})
        self.qs = self.qs.filter(q_objects)

    def filter_album(self):
        # Filter by album name (supports comma-separated values)
        value = self.params.get("album")
        if not value:
            return
        values = self._parse_str_list(value)
        if not values:
            return
        field_name = f"{self.field_prefix}album"
        q_objects = Q()
        for v in values:
            q_objects |= Q(**{f"{field_name}__icontains": v})
        self.qs = self.qs.filter(q_objects)

    def _parse_str_list(self, value):
        return [v.strip() for v in value.split(",") if v.strip()]
