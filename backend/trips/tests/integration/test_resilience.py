import json

import httpx
import pytest

from trips.api import rate_limit
from trips.providers import http_client

from .conftest import OSRM_URL, PHOTON_URL, osrm_ok, osrm_route, trip_payload


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(http_client, "_sleep", sleeps.append)
    return sleeps


def error_of(res):
    return res.json()["error"]


def test_routing_timeout_maps_to_504_and_is_retried(mock_api, analyze):
    route = mock_api.get(url__startswith=OSRM_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    res = analyze(trip_payload())
    assert res.status_code == 504
    err = error_of(res)
    assert err["code"] == "ROUTING_PROVIDER_TIMEOUT" and err["retryable"] is True
    assert route.call_count == 3  # 1 try + 2 bounded retries


def test_routing_connection_failure_is_503(mock_api, analyze):
    mock_api.get(url__startswith=OSRM_URL).mock(side_effect=httpx.ConnectError("down"))
    res = analyze(trip_payload())
    assert res.status_code == 503 and error_of(res)["code"] == "ROUTING_PROVIDER_UNAVAILABLE"


def test_429_is_retried_with_retry_after_then_succeeds(mock_api, analyze, _no_sleep):
    # weather mocked via the happy-path helper in the other module is not needed: use one route + failing weather
    responses = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(200, json=osrm_ok([osrm_route(0)])),
    ]
    route = mock_api.get(url__startswith=OSRM_URL).mock(side_effect=responses)
    mock_api.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(500))
    assert analyze(trip_payload()).status_code == 200
    assert route.call_count == 2 and _no_sleep[0] == 2.0


def test_persistent_429_maps_to_retryable_503(mock_api, analyze):
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(429))
    res = analyze(trip_payload())
    assert res.status_code == 503 and error_of(res)["code"] == "ROUTING_PROVIDER_RATE_LIMITED"


def test_4xx_is_not_retried(mock_api, analyze):
    route = mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(400))
    res = analyze(trip_payload())
    assert route.call_count == 1 and res.status_code == 502 and error_of(res)["retryable"] is False


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"<html>oops</html>"),
        httpx.Response(200, json={"code": "Ok", "routes": [{"distance": 1}]}),
        httpx.Response(200, json={"code": "Ok", "routes": [{"geometry": {"coordinates": [[500, 500], [1, 1]]}, "distance": 5, "duration": 5}]}),
        httpx.Response(200, json=["unexpected"]),
    ],
)
def test_malformed_routing_payload_is_502_without_leaking_details(mock_api, analyze, response):
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=response)
    res = analyze(trip_payload())
    assert res.status_code == 502 and error_of(res)["code"] == "ROUTING_PROVIDER_BAD_RESPONSE"
    assert "Traceback" not in res.content.decode() and "oops" not in res.content.decode()


def test_unexpected_exception_is_generic_500(mock_api, analyze, monkeypatch):
    from trips.services import trip_analyzer

    def boom(self, trip):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(trip_analyzer.TripAnalyzer, "analyze", boom)
    res = analyze(trip_payload())
    assert res.status_code == 500
    assert "secret" not in res.content.decode() and error_of(res)["code"] == "INTERNAL_ERROR"


def test_validation_errors_are_field_level_400(analyze):
    res = analyze(trip_payload(load_weight_lb=-1, checkpoint_interval_miles=12))
    err = error_of(res)
    assert res.status_code == 400 and err["code"] == "VALIDATION_ERROR"
    assert set(err["details"]["fields"]) == {"load_weight_lb", "checkpoint_interval_miles"}


def test_invalid_json_and_wrong_method(client):
    assert client.post("/api/trips/analyze/", data="{", content_type="application/json").status_code == 400
    res = client.get("/api/trips/analyze/")
    assert res.status_code == 405 and res.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert client.get("/api/nope/").status_code == 404


def test_application_rate_limit_returns_429_with_retry_after(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(200, json={"features": []}))
    for _ in range(90):
        assert client.get("/api/geocode/", {"q": "Denver"}).status_code == 200
    res = client.get("/api/geocode/", {"q": "Denver"})
    assert res.status_code == 429 and res["Retry-After"] and error_of(res)["retryable"]
    rate_limit.reset()


def test_health(client):
    assert client.get("/api/health/").json() == {"status": "ok"}
