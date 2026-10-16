"""Serialises domain objects to the documented JSON response shape (GeoJSON geometry)."""
from config import app_settings as cfg

from ..domain.enums import RiskLevel
from ..domain.geo import METERS_PER_MILE, simplify_line


def _miles(meters):
    return round(meters / METERS_PER_MILE, 2)


def _geometry(route):
    simplified = simplify_line(route.coordinates, cfg.GEOMETRY_SIMPLIFY_TOLERANCE_DEG)
    return {"type": "LineString", "coordinates": [[round(lon, 5), round(lat, 5)] for lon, lat in simplified]}


def _checkpoint(cp):
    weather = None
    if cp.weather:
        w = cp.weather
        weather = {
            "wind_mph": w.wind_mph,
            "rain_inches_per_hour": None if w.rain_in_per_hr is None else round(w.rain_in_per_hr, 3),
            "snow_inches_per_hour": None if w.snow_in_per_hr is None else round(w.snow_in_per_hr, 3),
            "forecast_time": w.forecast_time.isoformat(),
        }
    return {
        "id": cp.id,
        "index": cp.index,
        "distance_along_route_miles": _miles(cp.distance_m),
        "latitude": round(cp.latitude, 5),
        "longitude": round(cp.longitude, 5),
        "eta": cp.eta.isoformat(),
        "weather": weather,
        "condition_risks": {k: v.value for k, v in cp.condition_risks.items()},
        "overall_risk": cp.overall_risk.value,
        "data_status": cp.data_status.value,
    }


def _risk_summary(summary):
    return {
        "no_travel": summary.has_no_travel,
        "no_travel_miles": round(summary.no_travel_miles, 1),
        "severe_miles": round(summary.severe_miles, 1),
        "high_miles": round(summary.high_miles, 1),
        "moderate_miles": round(summary.miles(RiskLevel.MODERATE), 1),
        "low_miles": round(summary.miles(RiskLevel.LOW), 1),
        "unknown_miles": round(summary.unknown_miles, 1),
        "average_risk_score": None if summary.average_risk_score is None else round(summary.average_risk_score, 2),
    }


def _route(analysis):
    route = analysis.route
    return {
        "id": route.id,
        "label": route.label,
        "rank": analysis.rank,
        "is_recommended": analysis.is_recommended,
        "explanation": analysis.explanation,
        "geometry": _geometry(route),
        "distance_miles": _miles(route.distance_m),
        "duration_seconds": round(route.duration_s),
        "eta": analysis.eta.isoformat(),
        "risk_summary": _risk_summary(analysis.summary),
        "checkpoints": [_checkpoint(cp) for cp in analysis.checkpoints],
    }


def _corridor(corridor):
    if corridor is None:
        return None
    return {
        "offset_hours": corridor.offset_hours,
        "times_utc": corridor.times_utc,
        "points": [
            {
                "latitude": p.latitude,
                "longitude": p.longitude,
                "wind_mph": p.wind_mph,
                "rain_inches_per_hour": p.rain_in,
                "snow_inches_per_hour": p.snow_in,
                "risk": [r.value for r in p.risk],
            }
            for p in corridor.points
        ],
    }


def build_analysis_response(result):
    trip = result.request
    rec = result.recommendation
    return {
        "status": result.status,
        "trip": {
            "origin": {"label": trip.origin.label, "latitude": trip.origin.latitude, "longitude": trip.origin.longitude},
            "destination": {
                "label": trip.destination.label,
                "latitude": trip.destination.latitude,
                "longitude": trip.destination.longitude,
            },
            "departure_at": trip.departure_at.isoformat(),
            "load_weight_lb": trip.load_weight_lb,
            "checkpoint_interval_miles": trip.checkpoint_interval_miles,
        },
        "recommendation": {
            "route_id": rec.route_id,
            "reason_codes": rec.reason_codes,
            "summary": rec.summary,
            "incomplete": rec.incomplete,
            "all_routes_unsafe": rec.all_routes_unsafe,
        },
        "routes": [_route(a) for a in result.analyses],
        "forecast": {
            "offset_min_hours": 0,
            "offset_max_hours": cfg.FORECAST_HORIZON_HOURS,
            "reference": "DEPARTURE",
        },
        "corridor": _corridor(result.corridor),
        "warnings": result.warnings,
    }
