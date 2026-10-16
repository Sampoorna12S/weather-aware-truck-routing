from datetime import datetime, timezone

import pytest

from trips.domain.entities import Checkpoint
from trips.domain.enums import RiskLevel as R
from trips.domain.geo import METERS_PER_MILE as MI
from trips.domain.segment_mileage import segment_bounds, summarize

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


def cp(i, start_mi, end_mi, risk):
    return Checkpoint(f"c{i}", i, start_mi * MI, 0, 0, NOW, start_mi * MI, end_mi * MI, overall_risk=risk)


def test_segment_bounds_use_midpoints_and_cover_total():
    assert segment_bounds([0, 10, 30], 40) == [(0, 5), (5, 20), (20, 40)]


def test_summary_sums_miles_per_level_without_double_counting():
    cps = [cp(0, 0, 12.5, R.LOW), cp(1, 12.5, 37.5, R.SEVERE), cp(2, 37.5, 50, R.HIGH)]
    s = summarize(cps)
    assert s.total_miles == pytest.approx(50)
    assert s.severe_miles == pytest.approx(25) and s.high_miles == pytest.approx(12.5)
    # distance-weighted: (0*12.5 + 3*25 + 2*12.5) / 50
    assert s.average_risk_score == pytest.approx(2.0)


def test_unknown_is_reported_separately_and_not_scored():
    s = summarize([cp(0, 0, 10, R.UNKNOWN), cp(1, 10, 20, R.LOW)])
    assert s.unknown_miles == pytest.approx(10) and s.known_miles == pytest.approx(10)
    assert s.average_risk_score == 0


def test_all_unknown_has_no_average():
    assert summarize([cp(0, 0, 10, R.UNKNOWN)]).average_risk_score is None


def test_no_travel_flag():
    s = summarize([cp(0, 0, 10, R.NO_TRAVEL)])
    assert s.has_no_travel and s.no_travel_miles == pytest.approx(10)
