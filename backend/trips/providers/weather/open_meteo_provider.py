"""Open-Meteo hourly forecast adapter.

Requests mph / inches with GMT unix timestamps. Rain is `rain + showers`; snow is
`snowfall`. Open-Meteo hourly precipitation is the total of the preceding hour,
which equals an inches-per-hour rate. Free API: non-commercial use only.
"""
from datetime import timezone

from config import app_settings as cfg

from ...domain.entities import HourlySeries
from ...domain.exceptions import WeatherProviderError
from ..http_client import request_json

HOURLY_FIELDS = "wind_speed_10m,rain,showers,snowfall"


def _clean(values, expected_len):
    if not isinstance(values, list) or len(values) != expected_len:
        raise WeatherProviderError("bad_response", "hourly array missing or wrong length")
    out = []
    for v in values:
        if v is None:
            out.append(None)
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
            out.append(float(v))
        else:
            raise WeatherProviderError("bad_response", f"unexpected hourly value {v!r}")
    return out


class OpenMeteoProvider:
    def __init__(self, base_url=None):
        self.base_url = (base_url or cfg.WEATHER_BASE_URL).rstrip("/")

    def fetch_hourly(self, points, start_utc, end_utc):
        """points: [(lat, lon)]. Returns a list of HourlySeries aligned with `points`."""
        if not points:
            return []
        payload = request_json(
            "GET",
            f"{self.base_url}/v1/forecast",
            WeatherProviderError,
            params={
                "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
                "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
                "hourly": HOURLY_FIELDS,
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "GMT",
                "timeformat": "unixtime",
                "start_hour": start_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                "end_hour": end_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
            },
        )
        items = payload if isinstance(payload, list) else [payload]
        if len(items) != len(points):
            raise WeatherProviderError("bad_response", f"expected {len(points)} locations, got {len(items)}")
        return [self._parse_location(item) for item in items]

    @staticmethod
    def _parse_location(item):
        try:
            hourly = item["hourly"]
            units = item.get("hourly_units", {})
            times = hourly["time"]
            if not isinstance(times, list) or not all(isinstance(t, int) for t in times):
                raise WeatherProviderError("bad_response", "invalid time array")
            if units.get("wind_speed_10m") not in ("mp/h", "mph") or units.get("rain") != "inch":
                raise WeatherProviderError("bad_response", f"unexpected units: {units!r}")
            n = len(times)
            wind = _clean(hourly["wind_speed_10m"], n)
            rain = _clean(hourly["rain"], n)
            showers = _clean(hourly["showers"], n)
            snow = _clean(hourly["snowfall"], n)
        except (KeyError, TypeError, AttributeError) as exc:
            raise WeatherProviderError("bad_response", f"malformed location payload: {exc!r}") from exc

        total_rain = [None if r is None and s is None else (r or 0.0) + (s or 0.0) for r, s in zip(rain, showers)]
        return HourlySeries(times=times, wind_mph=wind, rain_in=total_rain, snow_in=snow)
