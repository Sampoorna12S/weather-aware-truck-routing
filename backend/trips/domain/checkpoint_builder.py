"""Places checkpoints along a route at a fixed mile interval."""
from .entities import Checkpoint
from .eta_calculator import build_time_profile, eta_at
from .geo import METERS_PER_MILE, cumulative_distances_m, point_at_distance
from .segment_mileage import segment_bounds


def checkpoint_distances_m(total_m, interval_miles):
    """Start, every `interval_miles`, and the destination (never a duplicate end)."""
    step = interval_miles * METERS_PER_MILE
    distances = [0.0]
    d = step
    while d < total_m - 1:
        distances.append(d)
        d += step
    if total_m - distances[-1] > 1 or len(distances) == 1:
        distances.append(total_m)
    return distances


def build_checkpoints(route, interval_miles, departure_at):
    cumulative = cumulative_distances_m(route.coordinates, route.distance_m)
    total = cumulative[-1]
    profile = build_time_profile(route, cumulative)
    distances = checkpoint_distances_m(total, interval_miles)
    bounds = segment_bounds(distances, total)

    checkpoints = []
    for i, (distance, (seg_start, seg_end)) in enumerate(zip(distances, bounds)):
        lon, lat = point_at_distance(route.coordinates, cumulative, distance)
        checkpoints.append(
            Checkpoint(
                id=f"{route.id}_cp_{i}",
                index=i,
                distance_m=distance,
                latitude=lat,
                longitude=lon,
                eta=eta_at(departure_at, profile, distance),
                segment_start_m=seg_start,
                segment_end_m=seg_end,
            )
        )
    return checkpoints
