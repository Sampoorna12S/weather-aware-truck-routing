import { ROUTE_STYLES } from '../config/constants';

/** Route A/B/C keep a stable colour + dash pattern regardless of ranking order. */
export function routeStyleIndex(route) {
  const letter = route.id.slice(-1);
  const index = 'abc'.indexOf(letter);
  return index >= 0 ? index : 0;
}

export function routeStyle(route) {
  return ROUTE_STYLES[routeStyleIndex(route)] || ROUTE_STYLES[0];
}
