"""Builds the 0-48 h corridor weather grid used by the heatmap slider.

The whole grid is returned with the analysis so moving the slider needs no
extra request. Offsets are relative to departure (floored to the UTC hour);
each offset maps to the forecast hour `base + offset`.
"""
from datetime import datetime, timedelta, timezone

from config import app_settings as cfg

from ..domain.entities import Corridor, CorridorPoint
from ..domain.geo import METERS_PER_MILE, cumulative_distances_m, point_at_distance, snap_to_grid
from ..domain.risk_engine import assess_values


def select_points(routes):
    """Grid-snapped (lat, lon) points sampled along every route, de-duplicated and capped."""
    step = cfg.CORRIDOR_SAMPLE_MILES * METERS_PER_MILE
    points = {}
    for route in routes:
        cumulative = cumulative_distances_m(route.coordinates, route.distance_m)
        total = cumulative[-1]
        distances = [i * step for i in range(int(total // step) + 1)] + [total]
        for d in distances:
            lon, lat = point_at_distance(route.coordinates, cumulative, d)
            points[(snap_to_grid(lat, cfg.CORRIDOR_GRID_DEG), snap_to_grid(lon, cfg.CORRIDOR_GRID_DEG))] = None
    ordered = list(points)
    if len(ordered) > cfg.CORRIDOR_MAX_POINTS:
        stride = len(ordered) / cfg.CORRIDOR_MAX_POINTS
        ordered = [ordered[int(i * stride)] for i in range(cfg.CORRIDOR_MAX_POINTS)]
    return ordered


def build_corridor(points, weather_series, base_utc, load_weight_lb):
    """`weather_series`: {(lat, lon): HourlySeries | None}. Points without data are dropped."""
    offsets = list(range(cfg.FORECAST_HORIZON_HOURS + 1))
    epochs = [int((base_utc + timedelta(hours=h)).timestamp()) for h in offsets]
    corridor_points = []
    for point in points:
        series = weather_series.get(point)
        if series is None:
            continue
        wind, rain, snow, risk = [], [], [], []
        for epoch in epochs:
            values = series.values_at(epoch) or (None, None, None)
            w, r, s = values
            wind.append(None if w is None else round(w, 1))
            rain.append(None if r is None else round(r, 3))
            snow.append(None if s is None else round(s, 3))
            risk.append(assess_values(w, r, s, load_weight_lb)[1])
        corridor_points.append(CorridorPoint(point[0], point[1], wind, rain, snow, risk))
    times = [datetime.fromtimestamp(e, tz=timezone.utc).isoformat() for e in epochs]
    return Corridor(offset_hours=offsets, times_utc=times, points=corridor_points)
