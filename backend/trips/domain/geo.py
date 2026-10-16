"""Geometry helpers. Coordinates are (longitude, latitude) tuples, as in GeoJSON."""
import math
from bisect import bisect_right

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344


def haversine_m(lon1, lat1, lon2, lat2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def cumulative_distances_m(coords, total_m=None):
    """Distance from the start to every vertex. When `total_m` is given the result is
    scaled so the last vertex equals the provider's reported route distance."""
    cumulative = [0.0]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        cumulative.append(cumulative[-1] + haversine_m(lon1, lat1, lon2, lat2))
    if total_m and cumulative[-1] > 0:
        scale = total_m / cumulative[-1]
        cumulative = [d * scale for d in cumulative]
    return cumulative


def point_at_distance(coords, cumulative, distance_m):
    """Interpolated (lon, lat) at `distance_m` along the line."""
    if distance_m <= 0:
        return coords[0]
    if distance_m >= cumulative[-1]:
        return coords[-1]
    i = bisect_right(cumulative, distance_m) - 1
    span = cumulative[i + 1] - cumulative[i]
    t = 0.0 if span == 0 else (distance_m - cumulative[i]) / span
    (lon1, lat1), (lon2, lat2) = coords[i], coords[i + 1]
    return lon1 + (lon2 - lon1) * t, lat1 + (lat2 - lat1) * t


def simplify_line(coords, tolerance_deg):
    """Iterative Ramer-Douglas-Peucker. Used only to shrink the geometry sent to the map."""
    n = len(coords)
    if n < 3:
        return list(coords)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        x1, y1 = coords[start]
        x2, y2 = coords[end]
        dx, dy = x2 - x1, y2 - y1
        seg_len2 = dx * dx + dy * dy
        max_dist, index = 0.0, None
        for i in range(start + 1, end):
            px, py = coords[i]
            if seg_len2 == 0:
                dist = math.hypot(px - x1, py - y1)
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len2))
                dist = math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
            if dist > max_dist:
                max_dist, index = dist, i
        if index is not None and max_dist > tolerance_deg:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [c for c, k in zip(coords, keep) if k]


def snap_to_grid(value, grid_deg):
    return round(round(value / grid_deg) * grid_deg, 4)
