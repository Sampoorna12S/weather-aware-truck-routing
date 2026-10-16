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


def test_missing_segment_annotations_still_gives_etas(mock_api, analyze):
    mock_happy(mock_api, routes=[osrm_route(0, with_annotations=False)])
    cps = analyze(trip_payload()).json()["routes"][0]["checkpoints"]
    assert cps[0]["eta"] < cps[-1]["eta"]


def test_no_route_from_provider(mock_api, analyze):
    mock_api.get(url__startswith=OSRM_URL).mock(return_value=httpx.Response(200, json={"code": "NoRoute"}))
    res = analyze(trip_payload())
    assert res.status_code == 404 and res.json()["error"]["code"] == "ROUTE_NOT_FOUND"
