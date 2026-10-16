"""Photon (OpenStreetMap) search-as-you-type adapter.

The public demo is best-effort with no uptime guarantee; set PHOTON_BASE_URL to a
hosted or self-hosted instance for production use. Attribution: OpenStreetMap contributors.
"""
from config import app_settings as cfg

from ...domain.exceptions import GeocodingProviderError
from ..http_client import request_json


def _label(props):
    primary = props.get("name") or " ".join(
        p for p in (props.get("housenumber"), props.get("street")) if p
    )
    parts = [primary, props.get("city") or props.get("district"), props.get("state"), props.get("country")]
    seen, out = set(), []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            out.append(part)
    return ", ".join(out)


class PhotonProvider:
    def __init__(self, base_url=None):
        self.base_url = (base_url or cfg.PHOTON_BASE_URL).rstrip("/")

    def search(self, query, limit):
        payload = request_json(
            "GET",
            f"{self.base_url}/api/",
            GeocodingProviderError,
            params={"q": query, "limit": limit, "lang": "en"},
        )
        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            raise GeocodingProviderError("bad_response", "Photon payload missing features")

        results = []
        for feature in features:
            try:
                lon, lat = feature["geometry"]["coordinates"][:2]
                props = feature.get("properties", {})
                lon, lat = float(lon), float(lat)
            except (KeyError, TypeError, ValueError):
                continue  # skip malformed entries rather than guess coordinates
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                continue
            label = _label(props)
            if not label:
                continue
            results.append(
                {
                    "label": label,
                    "name": props.get("name") or label.split(",")[0],
                    "region": props.get("state") or "",
                    "country": props.get("country") or "",
                    "latitude": lat,
                    "longitude": lon,
                }
            )
        return results
