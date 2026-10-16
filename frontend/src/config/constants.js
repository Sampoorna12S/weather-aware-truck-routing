export const CHECKPOINT_INTERVALS = [10, 25, 50];
export const DEFAULT_INTERVAL = 25;
export const MAX_LOAD_LB = 200000;

export const DEPARTURE_PAST_TOLERANCE_HOURS = 1;
export const DEPARTURE_MAX_FUTURE_DAYS = 7;
export const FORECAST_MAX_HOURS = 48;

export const GEOCODE_MIN_CHARS = 3;
export const GEOCODE_DEBOUNCE_MS = 300;
export const ANALYSIS_TIMEOUT_MS = 90000;
export const GEOCODE_TIMEOUT_MS = 12000;

export const RISK_ORDER = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL', 'UNKNOWN'];

/** Every level has a colour AND a text symbol so risk never relies on colour alone. */
export const RISK_META = {
  LOW: { label: 'Low', symbol: 'L', color: '#2e9d57', rank: 0 },
  MODERATE: { label: 'Moderate', symbol: 'M', color: '#d9a400', rank: 1 },
  HIGH: { label: 'High', symbol: 'H', color: '#ef7d00', rank: 2 },
  SEVERE: { label: 'Severe', symbol: 'S', color: '#d62839', rank: 3 },
  NO_TRAVEL: { label: 'No Travel', symbol: 'X', color: '#5b1a8f', rank: 4 },
  UNKNOWN: { label: 'Unknown', symbol: '?', color: '#6b7280', rank: -1 },
};

/** Route line styles differ in colour and dash pattern. */
export const ROUTE_STYLES = [
  { color: '#1d4ed8', dash: null },
  { color: '#0f766e', dash: [3, 2] },
  { color: '#b45309', dash: [1, 1.6] },
];

export const HEATMAP_LAYERS = {
  risk: { label: 'Risk', unit: '', max: 4, description: 'Derived risk for your load' },
  wind: { label: 'Wind', unit: 'mph', max: 60, description: 'Wind speed' },
  rain: { label: 'Rain', unit: 'in/hr', max: 1.0, description: 'Rain intensity' },
  snow: { label: 'Snow', unit: 'in/hr', max: 3.0, description: 'Snowfall intensity' },
};
