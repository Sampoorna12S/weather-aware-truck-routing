import { ANALYSIS_TIMEOUT_MS } from '../config/constants';
import { request } from './httpClient';
import { fetchRouteWeather } from './weatherApi';

const toLocation = ({ label, latitude, longitude }) => ({ label, latitude, longitude });

/** Maps the form's draft/snapshot to the backend contract. */
export function buildAnalyzePayload(inputs) {
  return {
    origin: toLocation(inputs.origin),
    destination: toLocation(inputs.destination),
    departure_at: new Date(inputs.departureAt).toISOString(),
    load_weight_lb: Number(inputs.loadWeight),
    checkpoint_interval_miles: Number(inputs.interval),
  };
}

export function analyzeTrip(inputs, { signal } = {}) {
  return request('/api/trips/prepare/', {
    method: 'POST',
    body: buildAnalyzePayload(inputs),
    signal,
    timeoutMs: ANALYSIS_TIMEOUT_MS,
  }).then(async (prepared) => {
    const forecast = await fetchRouteWeather(prepared.weather, { signal });
    return request('/api/trips/score/', {
      method: 'POST',
      body: {
        token: prepared.token,
        weather: forecast.weather,
        provider_error: forecast.providerError,
      },
      signal,
      timeoutMs: ANALYSIS_TIMEOUT_MS,
    });
  });
}
