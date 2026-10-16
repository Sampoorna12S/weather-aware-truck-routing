"""Mocked-provider helpers shared by the integration tests."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
PHOTON_URL = "https://photon.komoot.io/api/"
GEOCODING_FALLBACK_URL = "https://geocoding-api.open-meteo.com/v1/search"


def osrm_route(offset_lat=0.0, miles=120.0, with_annotations=True):
    """A west->east line near the 40th parallel (1 deg lon ~ 53 mi)."""
    n = 40
    deg = miles / 53.0
    coords = [[-105.0 + i * deg / n, 40.0 + offset_lat * (1 - abs(2 * i / n - 1))] for i in range(n + 1)]
    meters = miles * 1609.344
    route = {"geometry": {"type": "LineString", "coordinates": coords}, "distance": meters, "duration": miles * 60.0}
    if with_annotations:
        route["legs"] = [{"annotation": {"duration": [miles * 60.0 / n] * n, "distance": [meters / n] * n}}]
    return route


def osrm_ok(routes):
    return {"code": "Ok", "routes": routes}


def weather_handler(wind=10.0, rain=0.0, snow=0.0, fail_when=None, null_when=None):
    """Responder that returns one location per requested coordinate."""

    def handler(request):
        params = request.url.params
        lats = params["latitude"].split(",")
        lons = params["longitude"].split(",")
        if fail_when and fail_when(lats, lons):
            return httpx.Response(500, json={"error": True})
        start = datetime.strptime(params["start_hour"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        end = datetime.strptime(params["end_hour"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        times, t = [], start
        while t <= end:
            times.append(int(t.timestamp()))
            t += timedelta(hours=1)
        out = []
        for lat, lon in zip(lats, lons):
            w = wind(float(lat), float(lon)) if callable(wind) else wind
            nulls = null_when and null_when(float(lat), float(lon))
            out.append(
                {
                    "hourly_units": {"time": "unixtime", "wind_speed_10m": "mp/h", "rain": "inch", "showers": "inch", "snowfall": "inch"},
                    "hourly": {
                        "time": times,
                        "wind_speed_10m": [None if nulls else w] * len(times),
                        "rain": [None if nulls else rain] * len(times),
                        "showers": [None if nulls else 0.0] * len(times),
                        "snowfall": [None if nulls else snow] * len(times),
                    },
                }
            )
        return httpx.Response(200, json=out if len(out) > 1 else out[0])

    return handler


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as router:
        yield router


def trip_payload(**overrides):
    depart = datetime.now(timezone.utc) + timedelta(hours=2)
    body = {
        "origin": {"label": "Denver, Colorado", "latitude": 39.74, "longitude": -104.99},
        "destination": {"label": "Kearney, Nebraska", "latitude": 40.7, "longitude": -99.08},
        "departure_at": depart.isoformat(),
        "load_weight_lb": 32000,
        "checkpoint_interval_miles": 25,
    }
    body.update(overrides)
    return body


@pytest.fixture
def analyze(client):
    def call(body):
        return client.post("/api/trips/analyze/", data=json.dumps(body), content_type="application/json")

    return call
