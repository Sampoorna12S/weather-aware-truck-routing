from django.core.cache import cache

from config import app_settings as cfg

from ..providers.geocoding.photon_provider import PhotonProvider


class GeocodingService:
    def __init__(self, provider=None):
        self.provider = provider or PhotonProvider()

    def search(self, query):
        """Cached place search. An empty list means "no match"; coordinates are never guessed."""
        key = "geo:" + query.lower()
        cached = cache.get(key)
        if cached is not None:
            return cached
        results = self.provider.search(query, cfg.GEOCODE_RESULT_LIMIT)
        cache.set(key, results, cfg.GEOCODE_CACHE_TTL_SECONDS)
        return results
