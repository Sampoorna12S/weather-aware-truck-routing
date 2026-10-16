"""OpenRouteService adapter (needs ORS_API_KEY). Supports an HGV profile.

ORS limits alternative routes to fairly short trips, so long hauls may return
a single route; the analyzer then warns instead of fabricating alternatives.
"""
from config import app_settings as cfg

from ...domain.entities import Route
from ...domain.exceptions import NoRouteFound, RoutingProviderError
from ..http_client import request_json
from .base import RoutingProvider, validate_geometry

ROUTE_LABELS = "ABC"


class OrsProvider(RoutingProvider):
    def __init__(self, base_url=None, api_key=None, profile=None):
        self.base_url = (base_url or cfg.ORS_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else cfg.ORS_API_KEY
        self.profile = profile or cfg.ORS_PROFILE

    def get_routes(self, origin, destination, max_routes):
        if not self.api_key:
            raise RoutingProviderError("rejected", "ORS_API_KEY is not configured")
        body = {
            "coordinates": [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude],
            ],
            "instructions": False,
        }
        if max_routes > 1:
            body["alternative_routes"] = {"target_count": max_routes, "share_factor": 0.6, "weight_factor": 1.4}
        try:
            payload = request_json(
                "POST",
                f"{self.base_url}/v2/directions/{self.profile}/geojson",
                RoutingProviderError,
                json_body=body,
                headers={"Authorization": self.api_key},
            )
        except RoutingProviderError as exc:
            # ORS answers 404 when no route can be found between the two points.
            if exc.kind == "rejected" and "HTTP 404" in str(exc.detail):
                raise NoRouteFound() from exc
            raise

        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list):
            raise RoutingProviderError("bad_response", "ORS payload missing features")

        routes = []
        for feature in features[:max_routes]:
            route = self._normalise(feature, len(routes))
            if route:
                routes.append(route)
        if not routes:
            raise RoutingProviderError("bad_response", "ORS returned no usable routes")
        return routes

    @staticmethod
    def _normalise(feature, index):
        try:
            coords = [tuple(p[:2]) for p in feature["geometry"]["coordinates"]]
            summary = feature["properties"]["summary"]
            distance, duration = float(summary["distance"]), float(summary["duration"])
        except (KeyError, TypeError, ValueError):
            return None
        if not validate_geometry(coords) or distance <= 0 or duration <= 0:
            return None
        return Route(
            id=f"route_{ROUTE_LABELS[index].lower()}",
            label=f"Route {ROUTE_LABELS[index]}",
            coordinates=coords,
            distance_m=distance,
            duration_s=duration,
        )
