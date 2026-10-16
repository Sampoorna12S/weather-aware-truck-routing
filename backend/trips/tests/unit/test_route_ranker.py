from datetime import datetime, timezone

from trips.domain.entities import Route, RouteAnalysis, RiskSummary
from trips.domain.enums import RiskLevel as R
from trips.domain.route_ranker import rank_routes

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


def make(rid, *, severe=0.0, high=0.0, no_travel=0.0, unknown=0.0, low=100.0, avg=0.5, duration=3600):
    miles = {lv: 0.0 for lv in R}
    miles[R.SEVERE], miles[R.HIGH], miles[R.NO_TRAVEL], miles[R.UNKNOWN], miles[R.LOW] = severe, high, no_travel, unknown, low
    summary = RiskSummary(miles, sum(miles.values()), avg)
    route = Route(rid, rid.upper(), [(0, 0), (1, 1)], 1000, duration)
    return RouteAnalysis(route=route, checkpoints=[], summary=summary, eta=NOW)


def ranked_ids(analyses):
    return [a.route.id for a in analyses]


def test_severe_miles_dominate_everything_else():
    a, b = make("a", severe=10, high=0, avg=0.1, duration=100), make("b", severe=5, high=90, avg=2.0, duration=9999)
    items = [a, b]
    rec = rank_routes(items)
    assert ranked_ids(items) == ["b", "a"] and rec.route_id == "b"
    assert "FEWER_SEVERE_MILES" in rec.reason_codes


def test_high_then_average_then_time():
    items = [make("a", high=5, avg=1.0, duration=10), make("b", high=2, avg=3.0, duration=99)]
    assert rank_routes(items).route_id == "b"
    items = [make("a", avg=1.5, duration=10), make("b", avg=0.5, duration=99)]
    assert rank_routes(items).route_id == "b"
    items = [make("a", duration=500), make("b", duration=400)]
    rec = rank_routes(items)
    assert rec.route_id == "b" and rec.reason_codes == ["SHORTEST_TRAVEL_TIME"]


def test_full_tie_is_deterministic_by_provider_order():
    items = [make("a"), make("b"), make("c")]
    rec = rank_routes(items)
    assert ranked_ids(items) == ["a", "b", "c"]
    assert rec.reason_codes == ["TIED_ON_ALL_CRITERIA"]


def test_no_travel_routes_rank_after_safe_routes():
    items = [make("a", no_travel=5, severe=0), make("b", severe=40)]
    rec = rank_routes(items)
    assert rec.route_id == "b" and "AVOIDS_NO_TRAVEL" in rec.reason_codes
    assert "No Travel" in items[1].explanation


def test_all_routes_unsafe_is_flagged_not_endorsed():
    items = [make("a", no_travel=5), make("b", no_travel=9)]
    rec = rank_routes(items)
    assert rec.all_routes_unsafe and "No fully safe route" in rec.summary


def test_single_route():
    rec = rank_routes([make("a")])
    assert rec.reason_codes == ["ONLY_ROUTE_AVAILABLE"]


def test_no_weather_data_gives_no_recommendation():
    items = [make("a", low=0, unknown=100, avg=None), make("b", low=0, unknown=100, avg=None)]
    rec = rank_routes(items)
    assert rec.route_id is None and rec.incomplete and rec.reason_codes == ["NO_WEATHER_DATA"]


def test_partial_unknown_marks_recommendation_incomplete():
    rec = rank_routes([make("a", unknown=20, low=80), make("b", severe=10)])
    assert rec.route_id == "a" and rec.incomplete
