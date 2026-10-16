import { afterEach, describe, expect, it, vi } from 'vitest';
import { analyzeTrip } from './tripsApi';
import { fetchRouteWeather } from './weatherApi';

vi.mock('./weatherApi', () => ({
  fetchRouteWeather: vi.fn(),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('analyzeTrip', () => {
  it('prepares routes, fetches weather in the browser, then requests server scoring', async () => {
    const prepared = {
      token: 'signed-trip-token',
      weather: { points: [[9.9, 78.1]], start_utc: '2026-10-16T00:00:00+00:00', end_utc: '2026-10-17T00:00:00+00:00' },
    };
    const result = { status: 'COMPLETE', routes: [] };
    fetchRouteWeather.mockResolvedValue({ weather: [{ latitude: 9.9 }], providerError: null });
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => prepared })
      .mockResolvedValueOnce({ ok: true, json: async () => result });
    vi.stubGlobal('fetch', fetch);

    const analysis = await analyzeTrip({
      origin: { label: 'A', latitude: 1, longitude: 2 },
      destination: { label: 'B', latitude: 3, longitude: 4 },
      departureAt: '2026-10-16T10:00',
      loadWeight: '32000',
      interval: 25,
    });

    expect(fetchRouteWeather).toHaveBeenCalledWith(prepared.weather, { signal: undefined });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[0][0]).toBe('/api/trips/prepare/');
    expect(fetch.mock.calls[1][0]).toBe('/api/trips/score/');
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
      token: prepared.token,
      weather: [{ latitude: 9.9 }],
      provider_error: null,
    });
    expect(analysis).toBe(result);
  });
});