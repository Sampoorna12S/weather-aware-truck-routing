"""ETA estimation along a route.

Uses the provider's per-segment durations when they line up with the geometry;
otherwise the total duration is spread in proportion to distance (a uniform-speed
approximation). Provider durations come from a car profile, so ETAs are estimates,
not truck-certified navigation.
"""
from bisect import bisect_right
from datetime import timedelta


class TimeProfile:
    def __init__(self, cumulative_distance_m, cumulative_time_s):
        self._dist = cumulative_distance_m
        self._time = cumulative_time_s

    def seconds_at(self, distance_m):
        if distance_m <= 0:
            return 0.0
        if distance_m >= self._dist[-1]:
            return self._time[-1]
        i = bisect_right(self._dist, distance_m) - 1
        span = self._dist[i + 1] - self._dist[i]
        t = 0.0 if span == 0 else (distance_m - self._dist[i]) / span
        return self._time[i] + (self._time[i + 1] - self._time[i]) * t


def build_time_profile(route, cumulative_distance_m):
    total_distance = cumulative_distance_m[-1]
    durations = route.segment_durations_s
    usable = (
        durations
        and len(durations) == len(cumulative_distance_m) - 1
        and all(d >= 0 for d in durations)
        and sum(durations) > 0
    )
    if usable:
        scale = route.duration_s / sum(durations)  # keep the total equal to the route duration
        cumulative_time = [0.0]
        for d in durations:
            cumulative_time.append(cumulative_time[-1] + d * scale)
    elif total_distance > 0:
        cumulative_time = [d / total_distance * route.duration_s for d in cumulative_distance_m]
    else:
        cumulative_time = [0.0 for _ in cumulative_distance_m]
    return TimeProfile(cumulative_distance_m, cumulative_time)


def eta_at(departure_at, profile, distance_m):
    return departure_at + timedelta(seconds=profile.seconds_at(distance_m))
