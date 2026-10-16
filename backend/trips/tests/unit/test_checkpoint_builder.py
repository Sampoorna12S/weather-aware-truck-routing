from datetime import datetime, timedelta, timezone

import pytest

from trips.domain.checkpoint_builder import build_checkpoints, checkpoint_distances_m
from trips.domain.entities import Route
from trips.domain.eta_calculator import build_time_profile
from trips.domain.geo import METERS_PER_MILE, cumulative_distances_m

DEPART = datetime(2026, 10, 20, 8, 0, tzinfo=timezone(timedelta(hours=-6)))


def straight_route(miles, duration_s=3600.0, segment_durations=None):
    """A due-east line along the equator, ~miles long (1 deg lon ~ 69.17 mi)."""
    deg = miles / 69.17
    coords = [(i * deg / 10, 0.0) for i in range(11)]
    return Route("route_a", "Route A", coords, miles * METERS_PER_MILE, duration_s, segment_durations)


def test_distances_include_start_interval_marks_and_destination():
    d = checkpoint_distances_m(60 * METERS_PER_MILE, 25)
    assert [round(x / METERS_PER_MILE) for x in d] == [0, 25, 50, 60]


def test_distances_do_not_duplicate_destination_on_exact_multiple():
    d = checkpoint_distances_m(50 * METERS_PER_MILE, 25)
    assert [round(x / METERS_PER_MILE) for x in d] == [0, 25, 50]


def test_short_route_still_has_start_and_end():
    d = checkpoint_distances_m(4 * METERS_PER_MILE, 10)
    assert [round(x / METERS_PER_MILE) for x in d] == [0, 4]


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_segments_tile_the_route_exactly(interval):
    route = straight_route(137)
    cps = build_checkpoints(route, interval, DEPART)
    assert cps[0].segment_start_m == 0
    assert cps[-1].segment_end_m == pytest.approx(route.distance_m)
    for a, b in zip(cps, cps[1:]):
        assert a.segment_end_m == pytest.approx(b.segment_start_m)
    assert sum(c.segment_length_m for c in cps) == pytest.approx(route.distance_m)


def test_eta_proportional_when_no_segment_durations():
    cps = build_checkpoints(straight_route(100, duration_s=7200), 25, DEPART)
    assert cps[0].eta == DEPART
    assert cps[-1].eta == DEPART + timedelta(seconds=7200)
    assert (cps[2].eta - DEPART).total_seconds() == pytest.approx(3600, rel=0.01)  # mile 50 of 100


def test_eta_uses_segment_durations_when_aligned():
    # first half of the line takes 90% of the time
    durations = [360.0] * 5 + [40.0] * 5
    route = straight_route(100, duration_s=2000, segment_durations=durations)
    profile = build_time_profile(route, cumulative_distances_m(route.coordinates, route.distance_m))
    assert profile.seconds_at(route.distance_m / 2) == pytest.approx(1800)


def test_misaligned_segment_durations_fall_back_to_proportional():
    route = straight_route(100, duration_s=1000, segment_durations=[1.0, 2.0])
    profile = build_time_profile(route, cumulative_distances_m(route.coordinates, route.distance_m))
    assert profile.seconds_at(route.distance_m / 2) == pytest.approx(500, rel=0.01)


def test_eta_keeps_departure_timezone():
    cps = build_checkpoints(straight_route(50), 25, DEPART)
    assert all(c.eta.utcoffset() == timedelta(hours=-6) for c in cps)
