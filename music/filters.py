class SongQueryFilter:
    """
    Query-parameter filters for Song list endpoint.

    Supported query parameters:
    - search   : case-insensitive match on song title
    - artist   : case-insensitive match on artist
    - genre    : case-insensitive match on genre name
    - album    : case-insensitive match on album
    
    Invalid values result in an empty queryset (fail-soft) or are ignored.
    """

    def __init__(self, queryset, params):
        self.qs = queryset
        self.params = params

    def apply(self):
        self.search_title()
        self.filter_artist()
        self.filter_genre()
        self.filter_album()
        return self.qs

    def search_title(self):
        # Case-insensitive title search
        value = self.params.get("search")
        if not value:
            return
        self.qs = self.qs.filter(title__icontains=value.strip())

    def filter_artist(self):
        # Filter by artist name
        value = self.params.get("artist")
        if not value:
            return
        self.qs = self.qs.filter(artist__icontains=value.strip())

    def filter_genre(self):
        # Filter by genre name (related model)
        value = self.params.get("genre")
        if not value:
            return
        self.qs = self.qs.filter(genre__name__icontains=value.strip())

    def filter_album(self):
        # Filter by album name
        value = self.params.get("album")
        if not value:
            return
        self.qs = self.qs.filter(album__icontains=value.strip())

    def _parse_str_list(self, value):
        return [v.strip() for v in value.split(",") if v.strip()]
