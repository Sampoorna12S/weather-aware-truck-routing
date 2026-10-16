import { useCallback, useEffect, useState } from 'react';
import { searchLocations } from '../api/geocodeApi';
import { isAbortError } from '../api/httpClient';
import { GEOCODE_DEBOUNCE_MS, GEOCODE_MIN_CHARS } from '../config/constants';
import { useDebounce } from './useDebounce';

const IDLE = { status: 'idle', results: [], error: null };

/**
 * Debounced search-as-you-type. Obsolete queries are aborted, so a slow earlier
 * response can never overwrite the results of a newer query.
 */
export function useLocationSearch(text, enabled) {
  const query = useDebounce(text.trim(), GEOCODE_DEBOUNCE_MS);
  const [state, setState] = useState(IDLE);
  const [attempt, setAttempt] = useState(0);

  const active = enabled && query.length >= GEOCODE_MIN_CHARS && text.trim() === query;

  useEffect(() => {
    if (!active) {
      setState(IDLE);
      return undefined;
    }
    const controller = new AbortController();
    setState((previous) => ({ ...previous, status: 'loading', error: null }));
    searchLocations(query, { signal: controller.signal })
      .then((results) => setState({ status: 'success', results, error: null }))
      .catch((error) => {
        if (isAbortError(error)) return;
        setState({ status: 'error', results: [], error });
      });
    return () => controller.abort();
  }, [active, query, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const pending = enabled && text.trim().length >= GEOCODE_MIN_CHARS && !active;
  return { ...state, status: pending ? 'loading' : state.status, retry };
}
