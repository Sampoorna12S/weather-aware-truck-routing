import logging

from django.core.cache import cache

from config import app_settings as cfg

from ..domain.exceptions import GeocodingProviderError
from ..providers.geocoding.open_meteo_provider import OpenMeteoGeocodingProvider
from ..providers.geocoding.photon_provider import PhotonProvider

logger = logging.getLogger(__name__)


class GeocodingService:
    def __init__(self, provider=None, fallback_provider=None):
        self.provider = provider or PhotonProvider()
        self.fallback_provider = fallback_provider or OpenMeteoGeocodingProvider()

    def search(self, query):
        """Cached place search. An empty list means "no match"; coordinates are never guessed."""
        key = "geo:" + query.lower()
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            results = self.provider.search(query, cfg.GEOCODE_RESULT_LIMIT)
        except GeocodingProviderError as error:
            if error.kind not in {"timeout", "unavailable", "rate_limited"}:
                raise
            logger.warning("Photon unavailable; retrying location search with Open-Meteo: %s", error.detail)
            results = self.fallback_provider.search(query, cfg.GEOCODE_RESULT_LIMIT)
        cache.set(key, results, cfg.GEOCODE_CACHE_TTL_SECONDS)
        return results
