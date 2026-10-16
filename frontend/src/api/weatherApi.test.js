import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchRouteWeather } from './weatherApi';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchRouteWeather', () => {
  it('batches coordinates and normalizes Open-Meteo values', async () => {
    const times = [1792108800, 1792112400];
    const fetch = vi.fn(async (requestUrl) => {
      const url = new URL(requestUrl);
      const latitudes = url.searchParams.get('latitude').split(',');
      const longitudes = url.searchParams.get('longitude').split(',');
      const locations = latitudes.map((_, index) => ({
        hourly: {
          time: times,
          wind_speed_10m: [12, 13],
          rain: [0.1, null],
          showers: [0.05, null],
          snowfall: [0, null],
        },
      }));
      return {
        ok: true,
        json: async () => (locations.length === 1 ? locations[0] : locations),
      };
    });
    vi.stubGlobal('fetch', fetch);

    const result = await fetchRouteWeather({
      points: [[9.9, 78.1], [10.0, 78.2]],
      start_utc: '2026-10-16T00:00:00+00:00',
      end_utc: '2026-10-16T01:00:00+00:00',
    });

    expect(fetch).toHaveBeenCalledOnce();
    expect(result.providerError).toBeNull();
    expect(result.weather).toHaveLength(2);
    expect(result.weather[0].rain_inches_per_hour[0]).toBeCloseTo(0.15);
    expect(result.weather[0].rain_inches_per_hour[1]).toBeNull();
    expect(result.weather[0].wind_mph).toEqual([12, 13]);
  });

  it('reports rate limits so the backend marks weather as unknown', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 429 })));

    const result = await fetchRouteWeather({
      points: [[9.9, 78.1]],
      start_utc: '2026-10-16T00:00:00+00:00',
      end_utc: '2026-10-16T01:00:00+00:00',
    });

    expect(result).toEqual({ weather: [], providerError: 'rate_limited' });
  });
});
