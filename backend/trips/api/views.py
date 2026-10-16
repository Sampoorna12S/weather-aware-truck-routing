from django.http import JsonResponse
from django.views import View

from config import app_settings as cfg

from ..domain.exceptions import MethodNotAllowed, NotFound
from ..services.geocoding_service import GeocodingService
from ..services.trip_analyzer import TripAnalyzer
from . import rate_limit, validators
from .response_builders import build_analysis_response


class JsonView(View):
    """Raises (instead of returning HTML) so the middleware emits the JSON error contract."""

    def http_method_not_allowed(self, request, *args, **kwargs):
        raise MethodNotAllowed(details={"allowed": self._allowed_methods()})


class HealthView(JsonView):
    def get(self, request):
        return JsonResponse({"status": "ok"})


class GeocodeView(JsonView):
    def get(self, request):
        rate_limit.enforce(request, "geocode", cfg.RATE_LIMIT_GEOCODE_PER_MINUTE)
        query = validators.parse_geocode_query(request.GET.get("q"))
        return JsonResponse({"query": query, "results": GeocodingService().search(query)})


class AnalyzeTripView(JsonView):
    def post(self, request):
        rate_limit.enforce(request, "analyze", cfg.RATE_LIMIT_ANALYZE_PER_MINUTE)
        trip = validators.parse_trip_request(request.body)
        result = TripAnalyzer().analyze(trip)
        return JsonResponse(build_analysis_response(result))


def not_found(request, exception=None):
    from .middleware import error_response

    return error_response(NotFound(), getattr(request, "request_id", "-"))
