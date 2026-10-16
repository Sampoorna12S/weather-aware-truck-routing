import { DEFAULT_INTERVAL } from '../config/constants';

/** `YYYY-MM-DDTHH:mm` in local time, the format <input type="datetime-local"> uses. */
export function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function defaultDeparture(now = new Date()) {
  const next = new Date(now.getTime() + 60 * 60 * 1000);
  next.setMinutes(next.getMinutes() < 30 ? 30 : 60, 0, 0);
  return toLocalInputValue(next);
}

export function createInitialDraft() {
  return {
    origin: null,
    destination: null,
    departureAt: defaultDeparture(),
    loadWeight: '',
    interval: DEFAULT_INTERVAL,
  };
}

function locationKey(location) {
  return location ? `${location.latitude},${location.longitude}` : '';
}

/** True when the draft no longer matches the inputs behind the displayed result. */
export function draftDiffers(draft, analyzed) {
  if (!analyzed) return false;
  return (
    locationKey(draft.origin) !== locationKey(analyzed.origin) ||
    locationKey(draft.destination) !== locationKey(analyzed.destination) ||
    draft.departureAt !== analyzed.departureAt ||
    String(draft.loadWeight) !== String(analyzed.loadWeight) ||
    Number(draft.interval) !== Number(analyzed.interval)
  );
}
