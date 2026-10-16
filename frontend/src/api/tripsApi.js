import { ANALYSIS_TIMEOUT_MS } from '../config/constants';
import { request } from './httpClient';

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
  return request('/api/trips/analyze/', {
    method: 'POST',
    body: buildAnalyzePayload(inputs),
    signal,
    timeoutMs: ANALYSIS_TIMEOUT_MS,
  });
}
