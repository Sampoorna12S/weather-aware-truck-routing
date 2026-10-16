import json
from datetime import datetime, timedelta

import httpx

from .conftest import OSRM_URL, WEATHER_URL, osrm_ok, osrm_route, trip_payload, weather_handler


def mock_happy(mock_api, routes=None, **weather):
    routes = routes or [osrm_route(0), osrm_route(0.3), osrm_route(-0.3)]
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(200, json=osrm_ok(routes)))
    return mock_api.get(WEATHER_URL).mock(side_effect=weather_handler(**weather))


def test_three_routes_full_schema(mock_api, analyze):
    mock_happy(mock_api)
    res = analyze(trip_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "COMPLETE" and body["warnings"] == []
    assert [r["id"] for r in body["routes"]] and len(body["routes"]) == 3
    route = body["routes"][0]
    assert {"geometry", "distance_miles", "duration_seconds", "eta", "risk_summary", "checkpoints", "rank", "explanation"} <= set(route)
    assert route["geometry"]["type"] == "LineString"
    cp = route["checkpoints"][1]
    assert cp["weather"]["wind_mph"] == 10.0 and cp["overall_risk"] == "LOW" and cp["data_status"] == "AVAILABLE"
    assert cp["distance_along_route_miles"] == 25.0
    assert body["forecast"] == {"offset_min_hours": 0, "offset_max_hours": 48, "reference": "DEPARTURE"}
    assert len(body["corridor"]["times_utc"]) == 49 and body["corridor"]["points"]
    assert body["recommendation"]["route_id"] in {r["id"] for r in body["routes"]}
    assert res["X-Request-ID"]


def test_fewer_than_three_routes_warns_and_does_not_invent(mock_api, analyze):
    mock_happy(mock_api, routes=[osrm_route(0)])
    body = analyze(trip_payload()).json()
    assert len(body["routes"]) == 1
    assert body["warnings"][0]["code"] == "FEWER_ALTERNATIVES"
    assert body["recommendation"]["reason_codes"] == ["ONLY_ROUTE_AVAILABLE"]


def test_heavy_load_wind_override_produces_no_travel(mock_api, analyze):
    mock_happy(mock_api, wind=50.0)  # 45-54 mph + > 30,000 lb
    body = analyze(trip_payload(load_weight_lb=35000)).json()
    assert all(r["risk_summary"]["no_travel"] for r in body["routes"])
    assert body["recommendation"]["all_routes_unsafe"]
    assert any(w["code"] == "NO_SAFE_ROUTE" for w in body["warnings"])
    # same wind, light load -> Severe, not No Travel
    body = analyze(trip_payload(load_weight_lb=10000)).json()
    assert not any(r["risk_summary"]["no_travel"] for r in body["routes"])
    assert body["routes"][0]["risk_summary"]["severe_miles"] > 0


def test_recommends_route_with_calmer_weather(mock_api, analyze):
    # the northern route (higher latitude) gets windy; others stay calm
    mock_happy(mock_api, wind=lambda lat, lon: 40.0 if lat > 40.2 else 5.0)
    body = analyze(trip_payload(load_weight_lb=45000)).json()  # 35-44 mph + > 40,000 lb -> Severe
    best = next(r for r in body["routes"] if r["is_recommended"])
    assert best["risk_summary"]["severe_miles"] == min(r["risk_summary"]["severe_miles"] for r in body["routes"])
    assert body["routes"][0]["id"] == best["id"] and body["routes"][0]["rank"] == 1


def test_partial_weather_marks_unknown_not_safe(mock_api, analyze):
    mock_happy(mock_api, null_when=lambda lat, lon: lon > -103.5)
    body = analyze(trip_payload()).json()
    assert body["status"] == "PARTIAL"
    risks = {cp["overall_risk"] for r in body["routes"] for cp in r["checkpoints"]}
    assert "UNKNOWN" in risks
    assert all(r["risk_summary"]["unknown_miles"] > 0 for r in body["routes"])
    assert body["recommendation"]["incomplete"]


def test_weather_batch_failure_keeps_routes_and_flags_unknown(mock_api, analyze):
    routes = [osrm_route(0)]
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(200, json=osrm_ok(routes)))
    mock_api.get(WEATHER_URL).mock(return_value=httpx.Response(500))
    body = analyze(trip_payload()).json()
    assert body["status"] == "PARTIAL" and body["corridor"] is None
    assert any(w["code"] == "WEATHER_UNAVAILABLE" for w in body["warnings"])
    assert body["routes"][0]["risk_summary"]["unknown_miles"] > 0
    assert body["recommendation"]["route_id"] is None  # never claim safety without data


def test_weather_rate_limit_is_reported_as_retryable_guidance(mock_api, analyze):
    mock_api.get(url__startswith=OSRM_URL).mock(
        return_value=httpx.Response(200, json=osrm_ok([osrm_route(0)]))
    )
    mock_api.get(WEATHER_URL).mock(return_value=httpx.Response(429))

    body = analyze(trip_payload()).json()

    warning = next(item for item in body["warnings"] if item["code"] == "WEATHER_RATE_LIMITED")
    assert "rate limiting" in warning["message"]
    assert "re-analyze" in warning["message"]
    assert body["routes"][0]["checkpoints"][0]["overall_risk"] == "UNKNOWN"


def test_browser_weather_prepare_and_score_flow(mock_api, client):
    mock_api.get(url__startswith=OSRM_URL).mock(
        return_value=httpx.Response(200, json=osrm_ok([osrm_route(0)]))
    )
    prepared_response = client.post(
        "/api/trips/prepare/",
        data=json.dumps(trip_payload()),
        content_type="application/json",
    )
    assert prepared_response.status_code == 200
    prepared = prepared_response.json()
    assert prepared["weather"]["points"]

    start = datetime.fromisoformat(prepared["weather"]["start_utc"])
    end = datetime.fromisoformat(prepared["weather"]["end_utc"])
    times = []
    current = start
    while current <= end:
        times.append(int(current.timestamp()))
        current += timedelta(hours=1)
    weather = [
        {
            "latitude": latitude,
            "longitude": longitude,
            "times": times,
            "wind_mph": [10.0] * len(times),
            "rain_inches_per_hour": [0.0] * len(times),
            "snow_inches_per_hour": [0.0] * len(times),
        }
        for latitude, longitude in prepared["weather"]["points"]
    ]

    response = client.post(
        "/api/trips/score/",
        data=json.dumps({"token": prepared["token"], "weather": weather}),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETE"
    assert body["routes"][0]["checkpoints"][0]["overall_risk"] == "LOW"
    assert body["recommendation"]["route_id"] == "route_a"


def test_browser_weather_keeps_existing_risk_rules_and_route_ranking(mock_api, client):
    routes = [osrm_route(0), osrm_route(0.3), osrm_route(-0.3)]
    wind_for_point = lambda latitude, longitude: 40.0 if latitude > 40.2 else 5.0
    mock_happy(mock_api, routes=routes, wind=wind_for_point)
    inputs = trip_payload(load_weight_lb=45000)

    legacy_body = client.post(
        "/api/trips/analyze/",
        data=json.dumps(inputs),
        content_type="application/json",
    ).json()
    prepared = client.post(
        "/api/trips/prepare/",
        data=json.dumps(inputs),
        content_type="application/json",
    ).json()

    start = datetime.fromisoformat(prepared["weather"]["start_utc"])
    end = datetime.fromisoformat(prepared["weather"]["end_utc"])
    times = []
    current = start
    while current <= end:
        times.append(int(current.timestamp()))
        current += timedelta(hours=1)
    browser_weather = [
        {
            "latitude": latitude,
            "longitude": longitude,
            "times": times,
            "wind_mph": [wind_for_point(latitude, longitude)] * len(times),
            "rain_inches_per_hour": [0.0] * len(times),
            "snow_inches_per_hour": [0.0] * len(times),
        }
        for latitude, longitude in prepared["weather"]["points"]
    ]
    browser_body = client.post(
        "/api/trips/score/",
        data=json.dumps({"token": prepared["token"], "weather": browser_weather}),
        content_type="application/json",
    ).json()

    def risk_result(body):
        return {
            "routes": [
                {
                    "id": route["id"],
                    "rank": route["rank"],
                    "risk_summary": route["risk_summary"],
                    "checkpoints": [
                        (checkpoint["overall_risk"], checkpoint["condition_risks"])
                        for checkpoint in route["checkpoints"]
                    ],
                }
                for route in body["routes"]
            ],
            "recommendation": body["recommendation"],
        }

    assert risk_result(browser_body) == risk_result(legacy_body)


def test_browser_weather_score_rejects_unprepared_coordinates(mock_api, client):
    mock_api.get(url__startswith=OSRM_URL).mock(
        return_value=httpx.Response(200, json=osrm_ok([osrm_route(0)]))
    )
    prepared = client.post(
        "/api/trips/prepare/",
        data=json.dumps(trip_payload()),
        content_type="application/json",
    ).json()
    response = client.post(
        "/api/trips/score/",
        data=json.dumps(
            {
                "token": prepared["token"],
                "weather": [
                    {
                        "latitude": 0,
                        "longitude": 0,
                        "times": [],
                        "wind_mph": [],
                        "rain_inches_per_hour": [],
                        "snow_inches_per_hour": [],
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_browser_weather_rate_limit_scores_missing_data_as_unknown(mock_api, client):
    mock_api.get(url__startswith=OSRM_URL).mock(
        return_value=httpx.Response(200, json=osrm_ok([osrm_route(0)]))
    )
    prepared = client.post(
        "/api/trips/prepare/",
        data=json.dumps(trip_payload()),
        content_type="application/json",
    ).json()

    response = client.post(
        "/api/trips/score/",
        data=json.dumps(
            {
                "token": prepared["token"],
                "weather": [],
                "provider_error": "rate_limited",
            }
        ),
        content_type="application/json",
    )

    body = response.json()
    assert response.status_code == 200
    assert any(warning["code"] == "WEATHER_RATE_LIMITED" for warning in body["warnings"])
    assert body["routes"][0]["checkpoints"][0]["overall_risk"] == "UNKNOWN"
    assert body["recommendation"]["route_id"] is None


def test_missing_segment_annotations_still_gives_etas(mock_api, analyze):
    mock_happy(mock_api, routes=[osrm_route(0, with_annotations=False)])
    cps = analyze(trip_payload()).json()["routes"][0]["checkpoints"]
    assert cps[0]["eta"] < cps[-1]["eta"]


def test_no_route_from_provider(mock_api, analyze):
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(200, json={"code": "NoRoute"}))
    res = analyze(trip_payload())
    assert res.status_code == 404 and res.json()["error"]["code"] == "ROUTE_NOT_FOUND"
