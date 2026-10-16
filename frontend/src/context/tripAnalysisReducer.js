import { createInitialDraft } from '../utils/draft';

/**
 * State machine for the two-stage flow.
 *  - `draft`        what the user is editing (form or top bar)
 *  - `resultInputs` the exact inputs behind `result` (promoted together, atomically)
 *  - `pendingInputs` inputs of the request currently in flight
 *  - `requestId`    monotonically increasing token; late responses from older requests are ignored
 */
export const createInitialState = () => ({
  stage: 'setup',
  draft: createInitialDraft(),
  status: 'idle', // idle | loading | restarting | success | error
  result: null,
  resultInputs: null,
  resultId: null, // requestId that produced the result; lets views reset when a new result arrives
  pendingInputs: null,
  lastInputs: null, // inputs of the latest attempt, used by Retry
  error: null,
  requestId: 0,
});

export function tripAnalysisReducer(state, action) {
  switch (action.type) {
    case 'DRAFT_CHANGED':
      return { ...state, draft: { ...state.draft, [action.field]: action.value } };

    case 'ANALYSIS_STARTED':
      return {
        ...state,
        stage: 'results',
        status: action.restarting ? 'restarting' : 'loading',
        pendingInputs: action.inputs,
        lastInputs: action.inputs,
        error: null,
        requestId: action.requestId,
      };

    case 'ANALYSIS_SUCCEEDED':
      if (action.requestId !== state.requestId) return state; // superseded request
      return {
        ...state,
        status: 'success',
        result: action.result,
        resultId: action.requestId,
        resultInputs: action.inputs,
        pendingInputs: null,
        error: null,
      };

    case 'ANALYSIS_FAILED':
      if (action.requestId !== state.requestId) return state;
      return { ...state, status: 'error', pendingInputs: null, error: action.error };

    case 'RETURN_TO_SETUP':
      return { ...state, stage: 'setup', status: state.result ? 'success' : 'idle', error: null };

    default:
      return state;
  }
}

