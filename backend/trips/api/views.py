import json

from django.core import signing
from django.http import JsonResponse
from django.views import View

from config import app_settings as cfg

from ..domain.exceptions import MethodNotAllowed, NotFound, ValidationFailed
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


class PrepareTripView(JsonView):
    def post(self, request):
        rate_limit.enforce(request, "analyze", cfg.RATE_LIMIT_ANALYZE_PER_MINUTE)
        trip = validators.parse_trip_request(request.body)
        prepared = TripAnalyzer().prepare(trip)
        return JsonResponse(
            {
                "token": signing.dumps(prepared, salt="prepared-trip-weather-v1"),
                "weather": {
                    "points": prepared["weather_points"],
                    "start_utc": prepared["base_utc"],
                    "end_utc": prepared["end_utc"],
                },
            }
        )


class ScoreTripView(JsonView):
    def post(self, request):
        rate_limit.enforce(request, "score", cfg.RATE_LIMIT_ANALYZE_PER_MINUTE)
        if len(request.body) > cfg.MAX_WEATHER_SCORE_BODY_BYTES:
            raise ValidationFailed({}, "Weather data payload is too large.")
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            raise ValidationFailed({}, "Request body must be valid JSON.") from None
        if not isinstance(body, dict):
            raise ValidationFailed({}, "Request body must be a JSON object.")
        token = body.get("token")
        if not isinstance(token, str) or len(token) > cfg.MAX_WEATHER_SCORE_BODY_BYTES:
            raise ValidationFailed({"token": "Prepared trip token is missing or invalid."})
        try:
            prepared = signing.loads(
                token,
                salt="prepared-trip-weather-v1",
                max_age=cfg.PREPARED_TRIP_TOKEN_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            raise ValidationFailed({"token": "Prepared trip token is invalid or expired. Re-analyze the trip."}) from None

        batch = TripAnalyzer.weather_batch_from_payload(
            prepared,
            body.get("weather"),
            provider_error=body.get("provider_error"),
        )
        result = TripAnalyzer.score_prepared(prepared, batch)
        return JsonResponse(build_analysis_response(result))


def not_found(request, exception=None):
    from .middleware import error_response

    return error_response(NotFound(), getattr(request, "request_id", "-"))
