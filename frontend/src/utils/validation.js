import {
  CHECKPOINT_INTERVALS,
  DEPARTURE_MAX_FUTURE_DAYS,
  DEPARTURE_PAST_TOLERANCE_HOURS,
  MAX_LOAD_LB,
} from '../config/constants';

const HOUR_MS = 3600 * 1000;
const SAME_PLACE_DEGREES = 0.005; // ~500 m, mirrors the backend rule

export const FIELD_ORDER = ['origin', 'destination', 'departureAt', 'loadWeight', 'interval'];

export const FIELD_LABELS = {
  origin: 'Origin',
  destination: 'Destination',
  departureAt: 'Departure time',
  loadWeight: 'Load weight',
  interval: 'Checkpoint interval',
};

function isSamePlace(a, b) {
  return (
    Math.abs(a.latitude - b.latitude) < SAME_PLACE_DEGREES &&
    Math.abs(a.longitude - b.longitude) < SAME_PLACE_DEGREES
  );
}

function isResolved(location) {
  return (
    !!location &&
    typeof location.label === 'string' &&
    Number.isFinite(location.latitude) &&
    Number.isFinite(location.longitude)
  );
}

export function validateLocation(location, label) {
  return isResolved(location) ? '' : `Choose a ${label.toLowerCase()} from the suggestions.`;
}

export function validateDeparture(value, now = Date.now()) {
  if (!value) return 'Enter a departure date and time.';
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return 'Enter a valid date and time.';
  if (time < now - DEPARTURE_PAST_TOLERANCE_HOURS * HOUR_MS) return 'Departure cannot be in the past.';
  if (time > now + DEPARTURE_MAX_FUTURE_DAYS * 24 * HOUR_MS) {
    return `Forecasts only cover the next ${DEPARTURE_MAX_FUTURE_DAYS} days.`;
  }
  return '';
}

export function validateLoadWeight(value) {
  const text = String(value ?? '').trim();
  if (text === '') return 'Enter the load weight in pounds.';
  const weight = Number(text);
  if (!Number.isFinite(weight)) return 'Load weight must be a number.';
  if (weight <= 0) return 'Load weight must be greater than zero.';
  if (weight > MAX_LOAD_LB) return `Load weight cannot exceed ${MAX_LOAD_LB.toLocaleString('en-US')} lb.`;
  return '';
}

export function validateInterval(value) {
  return CHECKPOINT_INTERVALS.includes(Number(value)) ? '' : 'Choose 10, 25 or 50 miles.';
}

/** Returns { field: message } for every invalid field (empty object = valid). */
export function validateDraft(draft, now = Date.now()) {
  const errors = {
    origin: validateLocation(draft.origin, 'Origin'),
    destination: validateLocation(draft.destination, 'Destination'),
    departureAt: validateDeparture(draft.departureAt, now),
    loadWeight: validateLoadWeight(draft.loadWeight),
    interval: validateInterval(draft.interval),
  };
  if (!errors.origin && !errors.destination && isSamePlace(draft.origin, draft.destination)) {
    errors.destination = 'Destination must be different from the origin.';
  }
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message));
}

export function firstInvalidField(errors) {
  return FIELD_ORDER.find((field) => errors[field]) || null;
}
