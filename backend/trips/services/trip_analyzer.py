"""Orchestrates one end-to-end trip analysis: routes -> checkpoints -> weather -> risk -> ranking."""
import logging
from datetime import datetime, timedelta, timezone

from config import app_settings as cfg

from ..domain import risk_engine, segment_mileage
from ..domain.checkpoint_builder import build_checkpoints
from ..domain.entities import AnalysisResult, RouteAnalysis, WeatherSample
from ..domain.enums import DataStatus
from ..domain.geo import METERS_PER_MILE, snap_to_grid
from ..domain.route_ranker import rank_routes
from ..providers.routing.factory import get_routing_provider
from . import corridor_service
from .weather_service import WeatherService

logger = logging.getLogger(__name__)

HOUR = 3600


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
        batch = self.weather.fetch(checkpoint_points + corridor_points, base, end)
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

        analyses = [self._analyze_route(r, checkpoints_by_route[r.id], batch, trip) for r in routes]
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
            corridor_points, batch.series, base, trip.load_weight_lb
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
