import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { analyzeTrip } from '../../api/tripsApi';
import { isAbortError } from '../../api/httpClient';
import { createInitialState, tripAnalysisReducer } from '../tripAnalysisReducer';
import { validateDraft } from '../../utils/validation';

const TripAnalysisContext = createContext(null);

export function TripAnalysisProvider({ children }) {
  const [state, dispatch] = useReducer(tripAnalysisReducer, undefined, createInitialState);
  const controllerRef = useRef(null);
  const counterRef = useRef(0);
  const statusRef = useRef(state.status);
  statusRef.current = state.status;

  useEffect(() => () => controllerRef.current?.abort(), []);

  const runAnalysis = useCallback(async (inputs) => {
    // Only one analysis is ever active: abort the old request and invalidate its id.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const requestId = ++counterRef.current;
    const restarting = statusRef.current === 'loading' || statusRef.current === 'restarting';

    dispatch({ type: 'ANALYSIS_STARTED', requestId, inputs, restarting });
    try {
      const result = await analyzeTrip(inputs, { signal: controller.signal });
      dispatch({ type: 'ANALYSIS_SUCCEEDED', requestId, result, inputs });
    } catch (error) {
      if (isAbortError(error)) return; // intentional restart: not a user-facing failure
      dispatch({ type: 'ANALYSIS_FAILED', requestId, error });
    }
  }, []);

  /** Validates, then starts (or replaces) the analysis. Invalid input never cancels a running one. */
  const submit = useCallback(
    (draft) => {
      const errors = validateDraft(draft);
      if (Object.keys(errors).length > 0) return { ok: false, errors };
      runAnalysis({ ...draft });
      return { ok: true, errors: {} };
    },
    [runAnalysis],
  );

  const value = useMemo(
    () => ({
      state,
      setDraftField: (field, fieldValue) => dispatch({ type: 'DRAFT_CHANGED', field, value: fieldValue }),
      submit,
      retry: () => state.lastInputs && runAnalysis(state.lastInputs),
      returnToSetup: () => dispatch({ type: 'RETURN_TO_SETUP' }),
    }),
    [state, submit, runAnalysis],
  );

  return <TripAnalysisContext.Provider value={value}>{children}</TripAnalysisContext.Provider>;
}

export function useTripAnalysis() {
  const context = useContext(TripAnalysisContext);
  if (!context) throw new Error('useTripAnalysis must be used inside <TripAnalysisProvider>.');
  return context;
}
