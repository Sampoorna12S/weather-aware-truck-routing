import { describe, expect, it } from 'vitest';
import { firstInvalidField, validateDeparture, validateDraft, validateInterval, validateLoadWeight } from './validation';

const NOW = new Date('2026-10-15T12:00:00Z').getTime();
const place = (lat, lon) => ({ label: 'p', latitude: lat, longitude: lon });
const valid = () => ({
  origin: place(39.7, -104.9),
  destination: place(41.8, -87.6),
  departureAt: '2026-10-16T08:00',
  loadWeight: '32000',
  interval: 25,
});

describe('validation', () => {
  it('accepts a complete draft', () => {
    expect(validateDraft(valid(), NOW)).toEqual({});
  });

  it('requires resolved locations (typed text alone is not enough)', () => {
    const errors = validateDraft({ ...valid(), origin: null, destination: { label: 'typed' } }, NOW);
    expect(Object.keys(errors)).toEqual(['origin', 'destination']);
  });

  it('rejects identical origin and destination', () => {
    const errors = validateDraft({ ...valid(), destination: place(39.7001, -104.9001) }, NOW);
    expect(errors.destination).toMatch(/different/);
  });

  it.each([['', /Enter a departure/], ['nope', /valid/], ['2020-01-01T00:00', /past/], ['2027-01-01T00:00', /next 7 days/]])(
    'departure %s',
    (value, pattern) => expect(validateDeparture(value, NOW)).toMatch(pattern),
  );

  it.each([['', true], ['abc', true], ['0', true], ['-4', true], ['200001', true], ['1', false], ['200000', false], ['32000.5', false]])(
    'load weight %s invalid=%s',
    (value, invalid) => expect(Boolean(validateLoadWeight(value))).toBe(invalid),
  );

  it.each([[10, false], [25, false], [50, false], [15, true], ['', true]])('interval %s invalid=%s', (value, invalid) =>
    expect(Boolean(validateInterval(value))).toBe(invalid),
  );

  it('reports the first invalid field in form order', () => {
    expect(firstInvalidField({ loadWeight: 'x', departureAt: 'y' })).toBe('departureAt');
    expect(firstInvalidField({})).toBeNull();
  });
});
