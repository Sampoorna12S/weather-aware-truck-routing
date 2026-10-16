import pytest

from trips.domain.enums import DataStatus, RiskLevel as R
from trips.domain.risk_engine import (
    assess_values,
    classify_rain,
    classify_snow,
    classify_wind,
    overall_risk,
)

LIGHT = 10_000


@pytest.mark.parametrize(
    "wind,expected",
    [
        (0, R.LOW), (24.99, R.LOW), (25, R.MODERATE), (34.99, R.MODERATE),
        (35, R.HIGH), (44.99, R.HIGH), (45, R.SEVERE), (54.99, R.SEVERE),
        (55, R.NO_TRAVEL), (80, R.NO_TRAVEL),
    ],
)
def test_wind_bands_every_boundary(wind, expected):
    assert classify_wind(wind, LIGHT) is expected


@pytest.mark.parametrize(
    "rain,expected",
    [
        (0, R.LOW), (0.0999, R.LOW), (0.10, R.MODERATE), (0.2499, R.MODERATE),
        (0.25, R.HIGH), (0.4999, R.HIGH), (0.50, R.SEVERE), (1.00, R.SEVERE),
        (1.0001, R.NO_TRAVEL),
    ],
)
def test_rain_bands_every_boundary(rain, expected):
    assert classify_rain(rain) is expected


@pytest.mark.parametrize(
    "snow,expected",
    [
        (0.4999, R.LOW), (0.5, R.MODERATE), (0.9999, R.MODERATE), (1.0, R.HIGH),
        (1.9999, R.HIGH), (2.0, R.SEVERE), (3.0, R.SEVERE), (3.0001, R.NO_TRAVEL),
    ],
)
def test_snow_bands_every_boundary(snow, expected):
    assert classify_snow(snow) is expected


@pytest.mark.parametrize(
    "wind,load,expected",
    [
        (55, 1, R.NO_TRAVEL),            # >=55 is No Travel for any load
        (60, 5_000, R.NO_TRAVEL),
        (45, 30_000, R.SEVERE),          # load exactly 30,000 is NOT "> 30,000"
        (45, 30_001, R.NO_TRAVEL),
        (54.9, 45_000, R.NO_TRAVEL),
        (44.9, 30_001, R.HIGH),          # below the 45 mph band: override does not apply
        (35, 40_000, R.HIGH),            # load exactly 40,000 is NOT "> 40,000"
        (35, 40_001, R.SEVERE),
        (44.9, 60_000, R.SEVERE),
        (34.9, 60_000, R.MODERATE),      # below 35 mph: no override
    ],
)
def test_load_overrides(wind, load, expected):
    assert classify_wind(wind, load) is expected


def test_overall_is_worst_condition():
    risks, overall, status = assess_values(20, 0.3, 0.6, LIGHT)
    assert risks == {"wind": R.LOW, "rain": R.HIGH, "snow": R.MODERATE}
    assert overall is R.HIGH and status is DataStatus.AVAILABLE


def test_no_travel_wins_over_everything():
    assert assess_values(5, 0.0, 3.5, LIGHT)[1] is R.NO_TRAVEL


def test_missing_data_is_never_low():
    risks, overall, status = assess_values(None, None, None, LIGHT)
    assert overall is R.UNKNOWN and status is DataStatus.UNAVAILABLE
    # one field missing and the rest Low -> still unknown, not safe
    _, overall, status = assess_values(10, None, 0, LIGHT)
    assert overall is R.UNKNOWN and status is DataStatus.PARTIAL


def test_partial_data_keeps_known_elevated_risk():
    assert assess_values(40, None, 0, LIGHT)[1] is R.HIGH


def test_overall_risk_helper_with_all_unknown():
    assert overall_risk({"wind": R.UNKNOWN}) is R.UNKNOWN
