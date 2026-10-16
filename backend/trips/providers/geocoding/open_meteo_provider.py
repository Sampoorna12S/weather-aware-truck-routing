"""Open-Meteo city/place search fallback for Photon connectivity failures."""
from config import app_settings as cfg

from ...domain.exceptions import GeocodingProviderError
from ..http_client import request_json


class OpenMeteoGeocodingProvider:
    def __init__(self, base_url=None):
        self.base_url = base_url or cfg.GEOCODING_FALLBACK_URL

    def search(self, query, limit):
        payload = request_json(
            "GET",
            self.base_url,
            GeocodingProviderError,
            params={"name": query, "count": limit, "language": "en", "format": "json"},
        )
        places = payload.get("results", []) if isinstance(payload, dict) else None
        if not isinstance(places, list):
            raise GeocodingProviderError("bad_response", "Open-Meteo geocoding payload missing results")

        results = []
        for place in places:
            try:
                latitude = float(place["latitude"])
                longitude = float(place["longitude"])
                name = str(place["name"]).strip()
            except (KeyError, TypeError, ValueError):
                continue
            if not name or not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                continue
            admin1 = place.get("admin1") or ""
            country = place.get("country") or ""
            label = ", ".join(part for part in (name, admin1, country) if part)
            results.append(
                {
                    "label": label,
                    "name": name,
                    "region": admin1,
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )
        return results
