"""
Cache utilities for API response caching.
Provides key builders and invalidation helpers for list APIs.
"""
import hashlib
from django.core.cache import cache


# Cache TTLs (seconds)
GENRES_LIST_CACHE_TTL = 3600  # 1 hour
SONGS_LIST_CACHE_TTL = 300  # 5 minutes
TENANT_SONGS_LIST_CACHE_TTL = 300  # 5 minutes


def _hash_params(params: dict) -> str:
    """Create a stable hash from query params dict."""
    if not params:
        return "default"
    sorted_items = sorted(params.items())
    key_str = "|".join(f"{k}={v}" for k, v in sorted_items)
    return hashlib.md5(key_str.encode()).hexdigest()[:16]


def _get_version(key: str) -> int:
    """Get current cache version, default 1."""
    return cache.get(key, 1)


def _increment_version(key: str) -> int:
    """Increment cache version and return new value."""
    version = _get_version(key) + 1
    cache.set(key, version, timeout=None)
    return version


# --- Genres ---

GENRES_LIST_VERSION_KEY = "genres:list:version"


def get_genres_list_cache_key(page: int, page_size: int) -> str:
    """Build cache key for genres list."""
    version = _get_version(GENRES_LIST_VERSION_KEY)
    return f"genres:list:v{version}:p{page}:ps{page_size}"


def invalidate_genres_list_cache() -> None:
    """Invalidate genres list cache (call on create/update/delete genre)."""
    _increment_version(GENRES_LIST_VERSION_KEY)


# --- Songs ---

SONGS_LIST_VERSION_KEY = "songs:list:version"


def get_songs_list_cache_key(role: str, tenant_id: str | None, params_hash: str, page: int, page_size: int) -> str:
    """Build cache key for songs list."""
    version = _get_version(SONGS_LIST_VERSION_KEY)
    tenant_part = f"t{tenant_id}" if tenant_id else "global"
    return f"songs:list:v{version}:{role}:{tenant_part}:{params_hash}:p{page}:ps{page_size}"


def invalidate_songs_list_cache() -> None:
    """Invalidate songs list cache (call on create/update/delete song)."""
    _increment_version(SONGS_LIST_VERSION_KEY)


# --- Tenant Songs ---

TENANT_SONGS_LIST_VERSION_PREFIX = "tenant_songs:list:version"


def get_tenant_songs_list_version_key(tenant_id: str) -> str:
    """Version key for a specific tenant's songs list."""
    return f"{TENANT_SONGS_LIST_VERSION_PREFIX}:{tenant_id}"


def get_tenant_songs_list_cache_key(tenant_id: str, params_hash: str, page: int, page_size: int) -> str:
    """Build cache key for tenant songs list."""
    version = _get_version(get_tenant_songs_list_version_key(tenant_id))
    return f"tenant_songs:list:v{version}:t{tenant_id}:{params_hash}:p{page}:ps{page_size}"


def invalidate_tenant_songs_list_cache(tenant_id: str) -> None:
    """Invalidate tenant songs list cache for a tenant (call on add/remove tenant song)."""
    version_key = get_tenant_songs_list_version_key(str(tenant_id))
    _increment_version(version_key)


def get_song_list_params_hash(query_params) -> str:
    """Extract filter + pagination params for songs/tenant_songs cache key."""
    params = {}
    for k in ("title", "artist", "genre", "album", "page", "page_size"):
        v = query_params.get(k)
        if v is not None:
            params[k] = str(v)
    return _hash_params(params)