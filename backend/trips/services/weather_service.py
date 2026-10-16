"""Batched, de-duplicated, cached and concurrency-capped weather lookups.

A failed batch never aborts the analysis: its points come back as None and are
reported, so the caller can mark those checkpoints UNKNOWN instead of safe.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from django.core.cache import cache

from config import app_settings as cfg

from ..domain.exceptions import WeatherProviderError
from ..providers.weather.open_meteo_provider import OpenMeteoProvider

logger = logging.getLogger(__name__)


@dataclass
class WeatherBatch:
    series: dict  # (lat, lon) -> HourlySeries | None
    failed_points: int = 0
    last_error: WeatherProviderError = field(default=None)

    @property
    def all_failed(self):
        return bool(self.series) and all(s is None for s in self.series.values())


def _cache_key(point, start_utc, end_utc):
    lat, lon = point
    return f"wx:{lat:.2f}:{lon:.2f}:{int(start_utc.timestamp())}:{int(end_utc.timestamp())}"


class WeatherService:
    def __init__(self, provider=None):
        self.provider = provider or OpenMeteoProvider()

    def fetch(self, points, start_utc, end_utc):
        unique = list(dict.fromkeys(points))
        series, missing = {}, []
        for point in unique:
            cached = cache.get(_cache_key(point, start_utc, end_utc))
            if cached is not None:
                series[point] = cached
            else:
                missing.append(point)

        batch = WeatherBatch(series=series)
        chunks = [missing[i : i + cfg.WEATHER_BATCH_SIZE] for i in range(0, len(missing), cfg.WEATHER_BATCH_SIZE)]
        if chunks:
            with ThreadPoolExecutor(max_workers=min(cfg.WEATHER_MAX_WORKERS, len(chunks))) as pool:
                outcomes = list(pool.map(lambda c: self._fetch_chunk(c, start_utc, end_utc), chunks))
            for chunk, outcome in zip(chunks, outcomes):
                if isinstance(outcome, WeatherProviderError):
                    batch.last_error = outcome
                    batch.failed_points += len(chunk)
                    series.update({p: None for p in chunk})
                else:
                    for point, hourly in zip(chunk, outcome):
                        series[point] = hourly
                        cache.set(_cache_key(point, start_utc, end_utc), hourly, cfg.WEATHER_CACHE_TTL_SECONDS)
        return batch

    def _fetch_chunk(self, chunk, start_utc, end_utc):
        try:
            return self.provider.fetch_hourly(chunk, start_utc, end_utc)
        except WeatherProviderError as exc:
            logger.warning("Weather batch of %d points failed: %s", len(chunk), exc.detail)
            return exc
