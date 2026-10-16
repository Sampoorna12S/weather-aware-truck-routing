import httpx

from .conftest import GEOCODING_FALLBACK_URL, PHOTON_URL

PHOTON_PAYLOAD = {
    "features": [
        {
            "geometry": {"coordinates": [-104.9847, 39.7392]},
            "properties": {"name": "Denver", "state": "Colorado", "country": "United States"},
        },
        {"geometry": {"coordinates": ["bad", None]}, "properties": {"name": "Broken"}},
        {"geometry": {"coordinates": [999, 999]}, "properties": {"name": "Out of range"}},
        {
            "geometry": {"coordinates": [-87.62, 41.88]},
            "properties": {"street": "State St", "housenumber": "1", "city": "Chicago", "state": "Illinois", "country": "United States"},
        },
    ]
}


def test_normalised_results_skip_malformed_entries(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(200, json=PHOTON_PAYLOAD))
    res = client.get("/api/geocode/", {"q": "Denver"})
    results = res.json()["results"]
    assert res.status_code == 200 and len(results) == 2
    assert results[0] == {
        "label": "Denver, Colorado, United States", "name": "Denver", "region": "Colorado",
        "country": "United States", "latitude": 39.7392, "longitude": -104.9847,
    }
    assert results[1]["label"] == "1 State St, Chicago, Illinois, United States"


def test_no_match_returns_empty_list_not_guess(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(200, json={"features": []}))
    assert client.get("/api/geocode/", {"q": "zzzzqqq"}).json()["results"] == []


def test_short_query_rejected(client):
    res = client.get("/api/geocode/", {"q": "de"})
    assert res.status_code == 400 and "q" in res.json()["error"]["details"]["fields"]


def test_results_are_cached(mock_api, client):
    route = mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(200, json=PHOTON_PAYLOAD))
    client.get("/api/geocode/", {"q": "Denver"})
    client.get("/api/geocode/", {"q": "denver"})
    assert route.call_count == 1


def test_provider_failure_is_a_retryable_error(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(503))
    mock_api.get(GEOCODING_FALLBACK_URL).mock(return_value=httpx.Response(503))
    res = client.get("/api/geocode/", {"q": "Denver"})
    assert res.status_code == 503 and res.json()["error"] == {
        **res.json()["error"], "code": "GEOCODING_PROVIDER_UNAVAILABLE", "retryable": True,
    }


def test_photon_connection_failure_falls_back_to_open_meteo(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    mock_api.get(GEOCODING_FALLBACK_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Madurai",
                        "latitude": 9.919,
                        "longitude": 78.11953,
                        "admin1": "Tamil Nadu",
                        "country": "India",
                    }
                ]
            },
        )
    )

    response = client.get("/api/geocode/", {"q": "Madurai"})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "label": "Madurai, Tamil Nadu, India",
            "name": "Madurai",
            "region": "Tamil Nadu",
            "country": "India",
            "latitude": 9.919,
            "longitude": 78.11953,
        }
    ]


def test_malformed_provider_payload(mock_api, client):
    mock_api.get(url__startswith=PHOTON_URL).mock(return_value=httpx.Response(200, json={"oops": 1}))
    assert client.get("/api/geocode/", {"q": "Denver"}).status_code == 502
