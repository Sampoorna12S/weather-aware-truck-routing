import { WEATHER_BROWSER_BATCH_SIZE, WEATHER_BROWSER_CONCURRENCY, WEATHER_FETCH_TIMEOUT_MS } from '../config/constants';

const WEATHER_BASE_URL = (import.meta.env.VITE_WEATHER_BASE_URL || 'https://api.open-meteo.com').replace(/\/$/, '');
const HOURLY_FIELDS = 'wind_speed_10m,rain,showers,snowfall';

function validArray(value, length) {
  return Array.isArray(value) && value.length === length && value.every((item) =>
    item == null || (typeof item === 'number' && Number.isFinite(item) && item >= 0),
  );
}

function parseLocation(item, point) {
  const hourly = item?.hourly;
  const times = hourly?.time;
  const count = Array.isArray(times) ? times.length : -1;
  if (count < 1 || !times.every((value) => Number.isInteger(value))) throw new Error('Invalid Open-Meteo timestamps');

  const wind = hourly.wind_speed_10m;
  const rain = hourly.rain;
  const showers = hourly.showers;
  const snow = hourly.snowfall;
  if (![wind, rain, showers, snow].every((values) => validArray(values, count))) {
    throw new Error('Invalid Open-Meteo hourly values');
  }

  return {
    latitude: point[0],
    longitude: point[1],
    times,
    wind_mph: wind,
    rain_inches_per_hour: rain.map((value, index) =>
      value == null && showers[index] == null ? null : (value ?? 0) + (showers[index] ?? 0),
    ),
    snow_inches_per_hour: snow,
  };
}

async function fetchChunk(points, weather, signal) {
  const url = new URL(`${WEATHER_BASE_URL}/v1/forecast`);
  url.search = new URLSearchParams({
    latitude: points.map(([latitude]) => latitude.toFixed(4)).join(','),
    longitude: points.map(([, longitude]) => longitude.toFixed(4)).join(','),
    hourly: HOURLY_FIELDS,
    wind_speed_unit: 'mph',
    precipitation_unit: 'inch',
    timezone: 'GMT',
    timeformat: 'unixtime',
    start_hour: weather.start_utc.slice(0, 16),
    end_hour: weather.end_utc.slice(0, 16),
  });

  const controller = new AbortController();
  const onAbort = () => controller.abort();
  signal?.addEventListener('abort', onAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), WEATHER_FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      return { weather: [], error: response.status === 429 ? 'rate_limited' : 'unavailable' };
    }
    const payload = await response.json();
    const items = Array.isArray(payload) ? payload : [payload];
    if (items.length !== points.length) throw new Error('Unexpected Open-Meteo location count');
    return { weather: items.map((item, index) => parseLocation(item, points[index])), error: null };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { weather: [], error: 'unavailable' };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }
}

export async function fetchRouteWeather(weather, { signal } = {}) {
  const points = [...new Map(weather.points.map((point) => [`${point[0]},${point[1]}`, point])).values()];
  const chunks = [];
  for (let index = 0; index < points.length; index += WEATHER_BROWSER_BATCH_SIZE) {
    chunks.push(points.slice(index, index + WEATHER_BROWSER_BATCH_SIZE));
  }

  const results = [];
  let providerError = null;
  for (let index = 0; index < chunks.length; index += WEATHER_BROWSER_CONCURRENCY) {
    const group = await Promise.all(
      chunks.slice(index, index + WEATHER_BROWSER_CONCURRENCY).map((chunk) => fetchChunk(chunk, weather, signal)),
    );
    for (const result of group) {
      results.push(...result.weather);
      if (result.error === 'rate_limited') providerError = 'rate_limited';
      else if (result.error && !providerError) providerError = result.error;
    }
  }
  return { weather: results, providerError };
}
