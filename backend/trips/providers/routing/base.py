from abc import ABC, abstractmethod


class RoutingProvider(ABC):
    @abstractmethod
    def get_routes(self, origin, destination, max_routes):
        """Return up to `max_routes` normalised `Route` objects (best first).

        Must raise `RoutingProviderError` for upstream problems and `NoRouteFound`
        when the provider answers but no route exists. Must never invent routes.
        """


def validate_geometry(coords):
    """True when `coords` is a usable [(lon, lat), ...] line."""
    if not isinstance(coords, list) or len(coords) < 2:
        return False
    for point in coords:
        if not (isinstance(point, (list, tuple)) and len(point) >= 2):
            return False
        lon, lat = point[0], point[1]
        if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))):
            return False
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return False
    return True
