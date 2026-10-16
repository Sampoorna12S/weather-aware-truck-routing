import { describe, expect, it } from 'vitest';
import { createInitialState, tripAnalysisReducer as reduce } from './tripAnalysisReducer';

const inputs = (n) => ({ loadWeight: String(n) });

describe('tripAnalysisReducer', () => {
  it('starts on the setup stage with no result', () => {
    const state = createInitialState();
    expect(state.stage).toBe('setup');
    expect(state.result).toBeNull();
  });

  it('moves to the results stage when an analysis starts', () => {
    const state = reduce(createInitialState(), { type: 'ANALYSIS_STARTED', requestId: 1, inputs: inputs(1) });
    expect(state.stage).toBe('results');
    expect(state.status).toBe('loading');
  });

  it('ignores a late response from a superseded request', () => {
    let state = reduce(createInitialState(), { type: 'ANALYSIS_STARTED', requestId: 1, inputs: inputs(1) });
    state = reduce(state, { type: 'ANALYSIS_STARTED', requestId: 2, inputs: inputs(2), restarting: true });
    expect(state.status).toBe('restarting');
    state = reduce(state, { type: 'ANALYSIS_SUCCEEDED', requestId: 1, result: { id: 'old' }, inputs: inputs(1) });
    expect(state.result).toBeNull();
    expect(state.status).toBe('restarting');
    state = reduce(state, { type: 'ANALYSIS_SUCCEEDED', requestId: 2, result: { id: 'new' }, inputs: inputs(2) });
    expect(state.result).toEqual({ id: 'new' });
    expect(state.resultInputs).toEqual(inputs(2));
  });

  it('ignores a late failure from a superseded request', () => {
    let state = reduce(createInitialState(), { type: 'ANALYSIS_STARTED', requestId: 1, inputs: inputs(1) });
    state = reduce(state, { type: 'ANALYSIS_STARTED', requestId: 2, inputs: inputs(2), restarting: true });
    state = reduce(state, { type: 'ANALYSIS_FAILED', requestId: 1, error: { message: 'x' } });
    expect(state.error).toBeNull();
  });

  it('keeps the previous result (and its inputs) when a re-analysis fails', () => {
    let state = reduce(createInitialState(), { type: 'ANALYSIS_STARTED', requestId: 1, inputs: inputs(1) });
    state = reduce(state, { type: 'ANALYSIS_SUCCEEDED', requestId: 1, result: { id: 'a' }, inputs: inputs(1) });
    state = reduce(state, { type: 'ANALYSIS_STARTED', requestId: 2, inputs: inputs(2) });
    state = reduce(state, { type: 'ANALYSIS_FAILED', requestId: 2, error: { message: 'boom' } });
    expect(state.status).toBe('error');
    expect(state.result).toEqual({ id: 'a' });
    expect(state.resultInputs).toEqual(inputs(1));
  });

  it('draft edits never touch the displayed result', () => {
    let state = reduce(createInitialState(), { type: 'ANALYSIS_STARTED', requestId: 1, inputs: inputs(1) });
    state = reduce(state, { type: 'ANALYSIS_SUCCEEDED', requestId: 1, result: { id: 'a' }, inputs: inputs(1) });
    state = reduce(state, { type: 'DRAFT_CHANGED', field: 'loadWeight', value: '99' });
    expect(state.draft.loadWeight).toBe('99');
    expect(state.result).toEqual({ id: 'a' });
    expect(state.resultInputs).toEqual(inputs(1));
  });
});
