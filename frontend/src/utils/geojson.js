import { HEATMAP_LAYERS, RISK_META } from '../config/constants';

const emptyCollection = { type: 'FeatureCollection', features: [] };

export function routeFeature(route) {
  return { type: 'Feature', properties: { id: route.id }, geometry: route.geometry };
}

export function checkpointFeatures(route) {
  if (!route) return emptyCollection;
  return {
    type: 'FeatureCollection',
    features: route.checkpoints.map((cp) => ({
      type: 'Feature',
      properties: {
        routeId: route.id,
        checkpointId: cp.id,
        risk: cp.overall_risk,
        symbol: (RISK_META[cp.overall_risk] || RISK_META.UNKNOWN).symbol,
      },
      geometry: { type: 'Point', coordinates: [cp.longitude, cp.latitude] },
    })),
  };
}

function pointValue(point, layer, offset) {
  if (layer === 'risk') {
    const risk = point.risk[offset];
    return risk === 'UNKNOWN' || !RISK_META[risk] ? null : RISK_META[risk].rank;
  }
  const series = { wind: point.wind_mph, rain: point.rain_inches_per_hour, snow: point.snow_inches_per_hour }[layer];
  return series?.[offset];
}

/** Heatmap points for one forecast offset. Missing data is flagged, never rendered as safe. */
export function corridorFeatures(corridor, layer, offset) {
  if (!corridor) return emptyCollection;
  const max = HEATMAP_LAYERS[layer].max;
  return {
    type: 'FeatureCollection',
    features: corridor.points.map((point) => {
      const value = pointValue(point, layer, offset);
      return {
        type: 'Feature',
        properties: {
          weight: value == null ? 0 : Math.min(1, Math.max(0, value / max)),
          unknown: value == null ? 1 : 0,
        },
        geometry: { type: 'Point', coordinates: [point.longitude, point.latitude] },
      };
    }),
  };
}

export function routesBounds(routes) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const route of routes) {
    for (const [lon, lat] of route.geometry.coordinates) {
      minLon = Math.min(minLon, lon);
      maxLon = Math.max(maxLon, lon);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
    }
  }
  return Number.isFinite(minLon) ? [[minLon, minLat], [maxLon, maxLat]] : null;
}
