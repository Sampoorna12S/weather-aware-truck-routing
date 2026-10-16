"""Threshold constants from the assessment.

The written ranges overlap at their edges, so each band is interpreted as
half-open: a value belongs to the band whose lower bound it meets or exceeds.
The only closed upper edges are the top of Severe for rain and snow, because the
assessment defines No Travel there as strictly "> 1.00" and "> 3.0".
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    moderate_from: float
    high_from: float
    severe_from: float
    no_travel_at: float
    no_travel_inclusive: bool  # True: value >= no_travel_at; False: value > no_travel_at


WIND_MPH = Thresholds(25, 35, 45, 55, no_travel_inclusive=True)
RAIN_IN_PER_HR = Thresholds(0.10, 0.25, 0.50, 1.00, no_travel_inclusive=False)
SNOW_IN_PER_HR = Thresholds(0.5, 1.0, 2.0, 3.0, no_travel_inclusive=False)

# Load rules (wind only).
WIND_HEAVY_LOAD_NO_TRAVEL_LB = 30_000  # wind 45-54 mph and load > this -> No Travel
WIND_VERY_HEAVY_LOAD_SEVERE_LB = 40_000  # wind 35-44 mph and load > this -> Severe
WIND_HEAVY_LOAD_BAND = (45, 55)
WIND_VERY_HEAVY_LOAD_BAND = (35, 45)
