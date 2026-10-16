"""Turns point checkpoints into route segments and sums miles per risk level.

Each checkpoint owns the stretch of road halfway to each neighbour, so the
segments tile the route exactly: no mile is counted twice or skipped.
"""
from .entities import RiskSummary
from .enums import RiskLevel
from .geo import METERS_PER_MILE


def segment_bounds(distances_m, total_m):
    """[(start_m, end_m)] per checkpoint distance, tiling [0, total_m]."""
    if not distances_m:
        return []
    midpoints = [(a + b) / 2 for a, b in zip(distances_m, distances_m[1:])]
    starts = [0.0] + midpoints
    ends = midpoints + [total_m]
    return list(zip(starts, ends))


def summarize(checkpoints):
    miles_by_level = {level: 0.0 for level in RiskLevel}
    for cp in checkpoints:
        miles_by_level[cp.overall_risk] += cp.segment_length_m / METERS_PER_MILE
    total = sum(miles_by_level.values())

    scored_miles = sum(m for lv, m in miles_by_level.items() if lv.score is not None)
    average = None
    if scored_miles > 0:
        average = sum(lv.score * m for lv, m in miles_by_level.items() if lv.score is not None) / scored_miles
    return RiskSummary(miles_by_level=miles_by_level, total_miles=total, average_risk_score=average)
