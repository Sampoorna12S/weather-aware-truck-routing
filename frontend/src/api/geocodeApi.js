import { GEOCODE_TIMEOUT_MS } from '../config/constants';
import { request } from './httpClient';

export async function searchLocations(query, { signal } = {}) {
  const data = await request(`/api/geocode/?q=${encodeURIComponent(query)}`, {
    signal,
    timeoutMs: GEOCODE_TIMEOUT_MS,
  });
  return Array.isArray(data?.results) ? data.results : [];
}
