"""OSRM adapter (public demo server by default; car profile)."""
from config import app_settings as cfg

from ...domain.entities import Route
from ...domain.exceptions import NoRouteFound, RoutingProviderError
from ..http_client import request_json
from .base import RoutingProvider, validate_geometry

ROUTE_LABELS = "ABC"


class OsrmProvider(RoutingProvider):
    def __init__(self, base_url=None):
        self.base_url = (base_url or cfg.OSRM_BASE_URL).rstrip("/")

    def get_routes(self, origin, destination, max_routes):
        coords = f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        payload = request_json(
            "GET",
            f"{self.base_url}/route/v1/driving/{coords}",
            RoutingProviderError,
            params={
                "alternatives": max_routes,
                "overview": "full",
                "geometries": "geojson",
                "annotations": "duration,distance",
                "steps": "false",
            },
        )
        code = payload.get("code") if isinstance(payload, dict) else None
        if code in ("NoRoute", "NoSegment"):
            raise NoRouteFound()
        if code != "Ok" or not isinstance(payload.get("routes"), list):
            raise RoutingProviderError("bad_response", f"unexpected OSRM code/payload: {code!r}")

        routes = []
        for raw in payload["routes"][:max_routes]:
            route = self._normalise(raw, len(routes))
            if route:
                routes.append(route)
        if not routes:
            raise RoutingProviderError("bad_response", "OSRM returned no usable routes")
        return routes

    @staticmethod
    def _normalise(raw, index):
        try:
            coords = [tuple(p[:2]) for p in raw["geometry"]["coordinates"]]
            distance, duration = float(raw["distance"]), float(raw["duration"])
        except (KeyError, TypeError, ValueError):
            return None
        if not validate_geometry(coords) or distance <= 0 or duration <= 0:
            return None

        segment_durations = []
        try:
            for leg in raw.get("legs", []):
                segment_durations.extend(float(d) for d in leg["annotation"]["duration"])
        except (KeyError, TypeError, ValueError):
            segment_durations = None

        return Route(
            id=f"route_{ROUTE_LABELS[index].lower()}",
            label=f"Route {ROUTE_LABELS[index]}",
            coordinates=coords,
            distance_m=distance,
            duration_s=duration,
            segment_durations_s=segment_durations or None,
        )
