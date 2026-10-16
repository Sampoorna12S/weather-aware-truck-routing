"""Parses and validates request payloads. Raises ValidationFailed with per-field messages."""
import json
from datetime import datetime, timedelta, timezone

from config import app_settings as cfg

from ..domain.entities import Location, TripRequest
from ..domain.exceptions import ValidationFailed
from ..domain.geo import haversine_m


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return float(value)


def _parse_location(raw, field, errors):
    if not isinstance(raw, dict):
        errors[field] = "Select a location from the suggestions."
        return None
    label = raw.get("label")
    lat, lon = _number(raw.get("latitude")), _number(raw.get("longitude"))
    if not isinstance(label, str) or not label.strip() or len(label) > 300:
        errors[field] = "Location needs a label."
        return None
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        errors[field] = "Location coordinates are invalid."
        return None
    return Location(label=label.strip(), latitude=lat, longitude=lon)


def _parse_departure(raw, errors, now):
    if not isinstance(raw, str) or not raw.strip():
        errors["departure_at"] = "Enter a departure date and time."
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        errors["departure_at"] = "Departure must be a valid ISO 8601 date and time."
        return None
    if parsed.tzinfo is None:
        errors["departure_at"] = "Departure must include a timezone offset."
        return None
    earliest = now - timedelta(hours=cfg.DEPARTURE_PAST_TOLERANCE_HOURS)
    latest = now + timedelta(days=cfg.DEPARTURE_MAX_FUTURE_DAYS)
    if parsed < earliest:
        errors["departure_at"] = "Departure cannot be in the past."
    elif parsed > latest:
        errors["departure_at"] = f"Forecasts only cover the next {cfg.DEPARTURE_MAX_FUTURE_DAYS} days."
    else:
        return parsed
    return None


def parse_trip_request(body, now=None):
    now = now or datetime.now(timezone.utc)
    if len(body) > cfg.MAX_REQUEST_BODY_BYTES:
        raise ValidationFailed({}, "Request body is too large.")
    try:
        data = json.loads(body or b"{}")
    except ValueError:
        raise ValidationFailed({}, "Request body must be valid JSON.") from None
    if not isinstance(data, dict):
        raise ValidationFailed({}, "Request body must be a JSON object.")

    errors = {}
    origin = _parse_location(data.get("origin"), "origin", errors)
    destination = _parse_location(data.get("destination"), "destination", errors)
    if origin and destination:
        separation = haversine_m(origin.longitude, origin.latitude, destination.longitude, destination.latitude)
        if separation < cfg.MIN_TRIP_SEPARATION_METERS:
            errors["destination"] = "Destination must be different from the origin."

    departure = _parse_departure(data.get("departure_at"), errors, now)

    weight = _number(data.get("load_weight_lb"))
    if weight is None or weight <= 0:
        errors["load_weight_lb"] = "Load weight must be a positive number."
        weight = None
    elif weight > cfg.MAX_LOAD_WEIGHT_LB:
        errors["load_weight_lb"] = f"Load weight cannot exceed {cfg.MAX_LOAD_WEIGHT_LB:,} lb."
        weight = None

    interval = data.get("checkpoint_interval_miles")
    if isinstance(interval, bool) or interval not in cfg.ALLOWED_CHECKPOINT_INTERVALS:
        errors["checkpoint_interval_miles"] = "Choose a checkpoint interval of 10, 25 or 50 miles."

    if errors:
        raise ValidationFailed(errors)
    return TripRequest(origin, destination, departure, weight, int(interval))


def parse_geocode_query(raw):
    query = (raw or "").strip()
    if len(query) < cfg.GEOCODE_MIN_QUERY_LENGTH:
        raise ValidationFailed({"q": f"Type at least {cfg.GEOCODE_MIN_QUERY_LENGTH} characters."})
    if len(query) > cfg.GEOCODE_MAX_QUERY_LENGTH:
        raise ValidationFailed({"q": "Search text is too long."})
    return query
