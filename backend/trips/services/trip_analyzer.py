"""Orchestrates one end-to-end trip analysis: routes -> checkpoints -> weather -> risk -> ranking."""
import logging
from datetime import datetime, timedelta, timezone
from math import isfinite

from config import app_settings as cfg

from ..domain import risk_engine, segment_mileage
from ..domain.checkpoint_builder import build_checkpoints
from ..domain.entities import (
    AnalysisResult,
    Checkpoint,
    HourlySeries,
    Location,
    Route,
    RouteAnalysis,
    TripRequest,
    WeatherSample,
)
from ..domain.enums import DataStatus
from ..domain.exceptions import ValidationFailed, WeatherProviderError
from ..domain.geo import METERS_PER_MILE, simplify_line, snap_to_grid
from ..domain.route_ranker import rank_routes
from ..providers.routing.factory import get_routing_provider
from . import corridor_service
from .weather_service import WeatherBatch, WeatherService

logger = logging.getLogger(__name__)

HOUR = 3600


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        return None
    return float(value)


def _validated_weather_values(values, point_index):
    parsed = []
    for value in values:
        if value is None:
            parsed.append(None)
            continue
        number = _finite_number(value)
        if number is None or number < 0:
            raise ValidationFailed({"weather": f"Weather values for point {point_index} are invalid."})
        parsed.append(number)
    return parsed


def _floor_hour_utc(moment):
    epoch = int(moment.timestamp())
    return datetime.fromtimestamp(epoch - epoch % HOUR, tz=timezone.utc)


def _checkpoint_key(checkpoint):
    grid = cfg.CHECKPOINT_WEATHER_GRID_DEG
    return snap_to_grid(checkpoint.latitude, grid), snap_to_grid(checkpoint.longitude, grid)


def _sample_for(checkpoint, series):
    """Forecast for the hour containing the ETA (rounded up, since hourly precipitation
    is the total of the preceding hour). Returns None when the hour is not covered."""
    if series is None:
        return None
    epoch = int(checkpoint.eta.timestamp())
    epoch += -epoch % HOUR  # ceil to the next full hour
    values = series.values_at(epoch)
    if values is None:
        return None
    return WeatherSample(datetime.fromtimestamp(epoch, tz=timezone.utc), *values)


class TripAnalyzer:
    def __init__(self, routing_provider=None, weather_service=None):
        self.routing = routing_provider or get_routing_provider()
        self.weather = weather_service or WeatherService()

    def analyze(self, trip):
        prepared = self.prepare(trip)
        batch = self.weather.fetch(
            [tuple(point) for point in prepared["weather_points"]],
            datetime.fromisoformat(prepared["base_utc"]),
            datetime.fromisoformat(prepared["end_utc"]),
        )
        return self.score_prepared(prepared, batch)

    def prepare(self, trip):
        """Build route/checkpoint state and coordinates needed by a weather client."""
        warnings = []
        routes = self.routing.get_routes(trip.origin, trip.destination, cfg.MAX_ROUTES)
        if len(routes) < cfg.MAX_ROUTES:
            warnings.append(
                {
                    "code": "FEWER_ALTERNATIVES",
                    "message": f"The routing service returned {len(routes)} distinct route option(s); "
                    f"up to {cfg.MAX_ROUTES} were requested. The number of alternatives depends on "
                    "the roads and the provider's coverage for this trip.",
                }
            )

        checkpoints_by_route = {
            r.id: build_checkpoints(r, trip.checkpoint_interval_miles, trip.departure_at) for r in routes
        }
        base = _floor_hour_utc(trip.departure_at)
        last_eta = max(cp.eta for cps in checkpoints_by_route.values() for cp in cps)
        end = max(base + timedelta(hours=cfg.FORECAST_HORIZON_HOURS), _floor_hour_utc(last_eta) + timedelta(hours=1))

        corridor_points = corridor_service.select_points(routes)
        checkpoint_points = [_checkpoint_key(cp) for cps in checkpoints_by_route.values() for cp in cps]
        weather_points = list(dict.fromkeys(checkpoint_points + corridor_points))
        return {
            "trip": {
                "origin": {
                    "label": trip.origin.label,
                    "latitude": trip.origin.latitude,
                    "longitude": trip.origin.longitude,
                },
                "destination": {
                    "label": trip.destination.label,
                    "latitude": trip.destination.latitude,
                    "longitude": trip.destination.longitude,
                },
                "departure_at": trip.departure_at.isoformat(),
                "load_weight_lb": trip.load_weight_lb,
                "checkpoint_interval_miles": trip.checkpoint_interval_miles,
            },
            "routes": [
                {
                    "id": route.id,
                    "label": route.label,
                    "coordinates": simplify_line(route.coordinates, cfg.GEOMETRY_SIMPLIFY_TOLERANCE_DEG),
                    "distance_m": route.distance_m,
                    "duration_s": route.duration_s,
                    "checkpoints": [
                        {
                            "id": checkpoint.id,
                            "index": checkpoint.index,
                            "distance_m": checkpoint.distance_m,
                            "latitude": checkpoint.latitude,
                            "longitude": checkpoint.longitude,
                            "eta": checkpoint.eta.isoformat(),
                            "segment_start_m": checkpoint.segment_start_m,
                            "segment_end_m": checkpoint.segment_end_m,
                        }
                        for checkpoint in checkpoints_by_route[route.id]
                    ],
                }
                for route in routes
            ],
            "warnings": warnings,
            "base_utc": base.isoformat(),
            "end_utc": end.isoformat(),
            "corridor_points": corridor_points,
            "weather_points": weather_points,
        }

    @staticmethod
    def weather_batch_from_payload(prepared, payload, provider_error=None):
        """Validate browser-fetched hourly arrays and align them to prepared points."""
        if not isinstance(payload, list):
            raise ValidationFailed({"weather": "Weather data must be a list."})
        expected = {tuple(point) for point in prepared["weather_points"]}
        if len(payload) > len(expected):
            raise ValidationFailed({"weather": "Too many weather points were submitted."})
        start_epoch = int(datetime.fromisoformat(prepared["base_utc"]).timestamp())
        end_epoch = int(datetime.fromisoformat(prepared["end_utc"]).timestamp())

        series = {}
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValidationFailed({"weather": f"Weather point {index} is invalid."})
            latitude = _finite_number(item.get("latitude"))
            longitude = _finite_number(item.get("longitude"))
            point = (latitude, longitude)
            if latitude is None or longitude is None or point not in expected or point in series:
                raise ValidationFailed({"weather": f"Weather point {index} does not match the prepared trip."})

            times = item.get("times")
            wind = item.get("wind_mph")
            rain = item.get("rain_inches_per_hour")
            snow = item.get("snow_inches_per_hour")
            if not all(isinstance(values, list) for values in (times, wind, rain, snow)):
                raise ValidationFailed({"weather": f"Weather arrays for point {index} are invalid."})
            if not (len(times) == len(wind) == len(rain) == len(snow)) or len(times) > 400:
                raise ValidationFailed({"weather": f"Weather arrays for point {index} have invalid lengths."})
            if not all(isinstance(timestamp, int) and not isinstance(timestamp, bool) for timestamp in times):
                raise ValidationFailed({"weather": f"Weather timestamps for point {index} are invalid."})
            if times != sorted(set(times)) or any(timestamp < start_epoch or timestamp > end_epoch for timestamp in times):
                raise ValidationFailed({"weather": f"Weather timestamps for point {index} are outside the prepared forecast."})
            values = [
                *_validated_weather_values(wind, index),
                *_validated_weather_values(rain, index),
                *_validated_weather_values(snow, index),
            ]
            count = len(times)
            series[point] = HourlySeries(
                times=times,
                wind_mph=values[:count],
                rain_in=values[count : count * 2],
                snow_in=values[count * 2 :],
            )

        for point in expected:
            series.setdefault(point, None)
        failed_points = sum(value is None for value in series.values())
        last_error = None
        if provider_error in {"rate_limited", "unavailable"}:
            last_error = WeatherProviderError(provider_error, "Browser weather fetch failed")
        return WeatherBatch(series=series, failed_points=failed_points, last_error=last_error)

    @staticmethod
    def score_prepared(prepared, batch):
        trip_data = prepared["trip"]
        trip = TripRequest(
            Location(**trip_data["origin"]),
            Location(**trip_data["destination"]),
            datetime.fromisoformat(trip_data["departure_at"]),
            float(trip_data["load_weight_lb"]),
            int(trip_data["checkpoint_interval_miles"]),
        )
        warnings = list(prepared["warnings"])
        if batch.failed_points:
            rate_limited = batch.last_error and batch.last_error.kind == "rate_limited"
            warnings.append(
                {
                    "code": (
                        "WEATHER_RATE_LIMITED"
                        if rate_limited
                        else "WEATHER_PARTIAL" if not batch.all_failed else "WEATHER_UNAVAILABLE"
                    ),
                    "message": (
                        "The weather service is rate limiting requests. Wait a little and re-analyze. "
                        "Affected checkpoints are marked unknown, not safe."
                        if rate_limited
                        else "Weather data could not be loaded for some locations. "
                        "Affected checkpoints are marked unknown, not safe."
                    ),
                }
            )

        routes = []
        for route_data in prepared["routes"]:
            route = Route(
                route_data["id"],
                route_data["label"],
                route_data["coordinates"],
                float(route_data["distance_m"]),
                float(route_data["duration_s"]),
            )
            checkpoints = [
                Checkpoint(
                    item["id"],
                    int(item["index"]),
                    float(item["distance_m"]),
                    float(item["latitude"]),
                    float(item["longitude"]),
                    datetime.fromisoformat(item["eta"]),
                    float(item["segment_start_m"]),
                    float(item["segment_end_m"]),
                )
                for item in route_data["checkpoints"]
            ]
            routes.append((route, checkpoints))

        analyses = [TripAnalyzer._analyze_route(route, checkpoints, batch, trip) for route, checkpoints in routes]
        for a in analyses:
            if a.summary.unknown_miles > 0.05:
                warnings.append(
                    {
                        "code": "ROUTE_UNEVALUATED_MILES",
                        "route_id": a.route.id,
                        "message": f"{a.route.label}: {a.summary.unknown_miles:.0f} of "
                        f"{a.summary.total_miles:.0f} miles could not be evaluated (no forecast data).",
                    }
                )

        recommendation = rank_routes(analyses)
        if recommendation.all_routes_unsafe:
            warnings.append({"code": "NO_SAFE_ROUTE", "message": recommendation.summary})

        corridor = None if batch.all_failed else corridor_service.build_corridor(
            [tuple(point) for point in prepared["corridor_points"]],
            batch.series,
            datetime.fromisoformat(prepared["base_utc"]),
            trip.load_weight_lb,
        )
        status = "PARTIAL" if any(w["code"] != "FEWER_ALTERNATIVES" and w["code"] != "NO_SAFE_ROUTE" for w in warnings) else "COMPLETE"
        return AnalysisResult(status, trip, analyses, recommendation, corridor, warnings)

    @staticmethod
    def _analyze_route(route, checkpoints, batch, trip):
        for cp in checkpoints:
            cp.weather = _sample_for(cp, batch.series.get(_checkpoint_key(cp)))
            cp.condition_risks, cp.overall_risk, cp.data_status = risk_engine.assess_sample(
                cp.weather, trip.load_weight_lb
            )
            if cp.weather is None:
                cp.data_status = DataStatus.UNAVAILABLE
        summary = segment_mileage.summarize(checkpoints)
        return RouteAnalysis(route=route, checkpoints=checkpoints, summary=summary, eta=checkpoints[-1].eta)
