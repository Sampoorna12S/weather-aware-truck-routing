import json
from datetime import datetime, timedelta, timezone

import pytest

from trips.api.validators import parse_geocode_query, parse_trip_request
from trips.domain.exceptions import ValidationFailed

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def payload(**overrides):
    body = {
        "origin": {"label": "Denver", "latitude": 39.74, "longitude": -104.99},
        "destination": {"label": "Chicago", "latitude": 41.88, "longitude": -87.63},
        "departure_at": (NOW + timedelta(hours=3)).isoformat(),
        "load_weight_lb": 32000,
        "checkpoint_interval_miles": 25,
    }
    body.update(overrides)
    return json.dumps(body).encode()


def fields_of(body):
    with pytest.raises(ValidationFailed) as exc:
        parse_trip_request(body, now=NOW)
    return exc.value.fields


def test_valid_request_parses():
    trip = parse_trip_request(payload(), now=NOW)
    assert trip.checkpoint_interval_miles == 25 and trip.load_weight_lb == 32000


@pytest.mark.parametrize(
    "override,field",
    [
        ({"origin": None}, "origin"),
        ({"origin": {"label": "x", "latitude": 95, "longitude": 0}}, "origin"),
        ({"destination": {"label": "", "latitude": 1, "longitude": 1}}, "destination"),
        ({"departure_at": "not a date"}, "departure_at"),
        ({"departure_at": "2026-10-20T08:00:00"}, "departure_at"),  # no offset
        ({"departure_at": (NOW - timedelta(days=1)).isoformat()}, "departure_at"),
        ({"departure_at": (NOW + timedelta(days=30)).isoformat()}, "departure_at"),
        ({"load_weight_lb": 0}, "load_weight_lb"),
        ({"load_weight_lb": -5}, "load_weight_lb"),
        ({"load_weight_lb": "heavy"}, "load_weight_lb"),
        ({"load_weight_lb": True}, "load_weight_lb"),
        ({"load_weight_lb": 10**7}, "load_weight_lb"),
        ({"checkpoint_interval_miles": 15}, "checkpoint_interval_miles"),
        ({"checkpoint_interval_miles": "25"}, "checkpoint_interval_miles"),
    ],
)
def test_invalid_fields_are_reported(override, field):
    assert field in fields_of(payload(**override))


def test_identical_origin_and_destination_rejected():
    same = {"label": "A", "latitude": 39.74, "longitude": -104.99}
    assert "destination" in fields_of(payload(origin=same, destination=same))


def test_multiple_errors_reported_together():
    assert len(fields_of(payload(load_weight_lb=0, checkpoint_interval_miles=7))) == 2


@pytest.mark.parametrize("body", [b"not json", b"[]", b'"str"'])
def test_bad_bodies_rejected(body):
    with pytest.raises(ValidationFailed):
        parse_trip_request(body, now=NOW)


def test_geocode_query_rules():
    assert parse_geocode_query("  Denver ") == "Denver"
    with pytest.raises(ValidationFailed):
        parse_geocode_query("de")
    with pytest.raises(ValidationFailed):
        parse_geocode_query("x" * 500)
