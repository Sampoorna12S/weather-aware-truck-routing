export function formatMiles(miles) {
  if (miles == null || Number.isNaN(miles)) return '—';
  return `${Math.round(miles).toLocaleString('en-US')} mi`;
}

export function formatMilesPrecise(miles) {
  if (miles == null || Number.isNaN(miles)) return '—';
  return `${miles.toLocaleString('en-US', { maximumFractionDigits: 1 })} mi`;
}

export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '—';
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes} min`;
  return `${hours} h ${String(minutes).padStart(2, '0')} min`;
}

const dateTimeFormat = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

export function formatDateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : dateTimeFormat.format(date);
}

const hourFormat = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  hour: 'numeric',
  timeZoneName: 'short',
});

export function formatForecastHour(iso) {
  if (!iso) return 'unavailable';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? 'unavailable' : hourFormat.format(date);
}

export function formatWeatherValue(value, unit, digits = 1) {
  if (value == null) return 'unavailable';
  return `${Number(value).toFixed(digits)} ${unit}`;
}

export function formatScore(score) {
  return score == null ? '—' : score.toFixed(2);
}

export function formatWeight(pounds) {
  return `${Number(pounds).toLocaleString('en-US')} lb`;
}
