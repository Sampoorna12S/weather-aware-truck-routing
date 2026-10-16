import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import mapLibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { MAP_STYLE_URL } from '../../config/env';
import { RISK_META } from '../../config/constants';
import { checkpointFeatures, corridorFeatures, routesBounds } from '../../utils/geojson';
import { formatDateTime, formatMilesPrecise, formatWeatherValue } from '../../utils/formatters';
import { routeStyle } from '../../utils/routeStyle';
import Button from '../common/Button';
import Spinner from '../common/Spinner';
import styles from './TripMap.module.css';

maplibregl.setWorkerUrl(mapLibreWorkerUrl);

const EMPTY = { type: 'FeatureCollection', features: [] };
const FALLBACK_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'osm-background', type: 'background', paint: { 'background-color': '#e5e7eb' } },
    { id: 'osm-raster', type: 'raster', source: 'osm' },
  ],
};

const RISK_COLORS = [
  'interpolate',
  ['linear'],
  ['heatmap-density'],
  0,
  'rgba(46,157,87,0)',
  0.15,
  '#2e9d57',
  0.35,
  '#d9a400',
  0.55,
  '#ef7d00',
  0.75,
  '#d62839',
  1,
  '#5b1a8f',
];

const WEATHER_COLORS = [
  'interpolate',
  ['linear'],
  ['heatmap-density'],
  0,
  'rgba(29,78,216,0)',
  0.2,
  '#93c5fd',
  0.45,
  '#2563eb',
  0.7,
  '#7c3aed',
  1,
  '#6b21a8',
];

function endpoints(result) {
  const trip = result?.trip;
  if (!trip) return EMPTY;
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { role: 'start', label: trip.origin.label },
        geometry: { type: 'Point', coordinates: [trip.origin.longitude, trip.origin.latitude] },
      },
      {
        type: 'Feature',
        properties: { role: 'end', label: trip.destination.label },
        geometry: { type: 'Point', coordinates: [trip.destination.longitude, trip.destination.latitude] },
      },
    ],
  };
}

function addBaseLayers(map) {
  map.addSource('corridor', { type: 'geojson', data: EMPTY });
  map.addSource('routes', { type: 'geojson', data: EMPTY });
  map.addSource('checkpoints', { type: 'geojson', data: EMPTY });
  map.addSource('ends', { type: 'geojson', data: EMPTY });

  map.addLayer({
    id: 'corridor-heat',
    type: 'heatmap',
    source: 'corridor',
    filter: ['==', ['get', 'unknown'], 0],
    paint: {
      'heatmap-weight': ['get', 'weight'],
      'heatmap-intensity': 0.9,
      'heatmap-radius': 28,
      'heatmap-opacity': 0.7,
      'heatmap-color': RISK_COLORS,
    },
  });
  map.addLayer({
    id: 'corridor-unknown',
    type: 'circle',
    source: 'corridor',
    filter: ['==', ['get', 'unknown'], 1],
    paint: {
      'circle-radius': 4,
      'circle-color': '#6b7280',
      'circle-stroke-width': 1,
      'circle-stroke-color': '#fff',
      'circle-opacity': 0.85,
    },
  });
  map.addLayer({
    id: 'routes-casing',
    type: 'line',
    source: 'routes',
    paint: {
      'line-color': '#0f172a',
      'line-width': ['case', ['get', 'selected'], 9, 6],
      'line-opacity': 0.18,
    },
  });
  map.addLayer({
    id: 'routes-line',
    type: 'line',
    source: 'routes',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': ['get', 'color'],
      'line-width': ['case', ['get', 'selected'], 6.5, 3.5],
      'line-opacity': ['case', ['get', 'hidden'], 0, 1],
    },
  });
  map.addLayer({
    id: 'ends',
    type: 'circle',
    source: 'ends',
    paint: {
      'circle-radius': 7,
      'circle-color': ['match', ['get', 'role'], 'start', '#111827', '#fff'],
      'circle-stroke-width': 2,
      'circle-stroke-color': ['match', ['get', 'role'], 'start', '#fff', '#111827'],
    },
  });
  map.addLayer({
    id: 'checkpoints',
    type: 'circle',
    source: 'checkpoints',
    paint: {
      'circle-radius': ['case', ['boolean', ['get', 'active'], false], 9, 6],
      'circle-color': [
        'match',
        ['get', 'risk'],
        'LOW',
        RISK_META.LOW.color,
        'MODERATE',
        RISK_META.MODERATE.color,
        'HIGH',
        RISK_META.HIGH.color,
        'SEVERE',
        RISK_META.SEVERE.color,
        'NO_TRAVEL',
        RISK_META.NO_TRAVEL.color,
        RISK_META.UNKNOWN.color,
      ],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#fff',
    },
  });
}

function routeCollection(routes, selectedRouteId, hiddenRouteIds) {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      properties: {
        id: route.id,
        selected: route.id === selectedRouteId,
        hidden: hiddenRouteIds.includes(route.id),
        color: routeStyle(route).color,
      },
      geometry: route.geometry,
    })),
  };
}

function checkpointCollection(routes, selectedRouteId, hiddenRouteIds, selectedCheckpoint) {
  const selected = routes.find((route) => route.id === selectedRouteId);
  const visible = selected && !hiddenRouteIds.includes(selected.id) ? selected : null;
  const features = checkpointFeatures(visible);
  if (selectedCheckpoint) {
    features.features = features.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        active: feature.properties.checkpointId === selectedCheckpoint.checkpointId,
      },
    }));
  }
  return features;
}

function checkpointPopupContent(route, checkpoint) {
  const content = document.createElement('div');
  content.className = styles.popup;

  const heading = document.createElement('h3');
  heading.className = styles.popupHeading;
  heading.textContent = `${route.label} checkpoint`;
  content.append(heading);

  const rows = [
    ['Distance along route', formatMilesPrecise(checkpoint.distance_along_route_miles)],
    ['Estimated arrival', formatDateTime(checkpoint.eta)],
    ['Forecast hour used', checkpoint.weather?.forecast_time ? formatDateTime(checkpoint.weather.forecast_time) : 'Unavailable'],
    ['Wind', formatWeatherValue(checkpoint.weather?.wind_mph, 'mph')],
    ['Rain', formatWeatherValue(checkpoint.weather?.rain_inches_per_hour, 'in/hr', 2)],
    ['Snow', formatWeatherValue(checkpoint.weather?.snow_inches_per_hour, 'in/hr', 2)],
  ];
  const list = document.createElement('dl');
  list.className = styles.popupRows;
  rows.forEach(([label, value]) => {
    const row = document.createElement('div');
    row.className = styles.popupRow;
    const term = document.createElement('dt');
    term.textContent = label;
    const description = document.createElement('dd');
    description.textContent = value;
    row.append(term, description);
    list.append(row);
  });

  const overall = document.createElement('div');
  overall.className = styles.popupOverall;
  const risk = document.createElement('span');
  risk.className = `${styles.popupRisk} ${styles[`risk${checkpoint.overall_risk}`] || styles.riskUNKNOWN}`;
  risk.textContent = `${RISK_META[checkpoint.overall_risk]?.label || RISK_META.UNKNOWN.label}`;
  overall.append(risk);
  if (checkpoint.data_status !== 'AVAILABLE') {
    const status = document.createElement('span');
    status.textContent = 'Unavailable';
    overall.append(status);
  }
  content.append(list, overall);
  return content;
}

export default function TripMap({ result, view, loading, onSelectRoute, onSelectCheckpoint }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const resultRef = useRef(result);
  resultRef.current = result;
  const callbacksRef = useRef({ onSelectRoute, onSelectCheckpoint });
  callbacksRef.current = { onSelectRoute, onSelectCheckpoint };
  const fittedFor = useRef(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [basemapFallback, setBasemapFallback] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const hasResult = Boolean(result);
  const originRef = useRef([-98, 39]);
  if (result?.trip?.origin) {
    originRef.current = [result.trip.origin.longitude, result.trip.origin.latitude];
  }

  useEffect(() => {
    if (!hasResult || !containerRef.current) return undefined;
    setFailed(false);
    setBasemapFallback(false);
    setReady(false);
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: originRef.current,
      zoom: 6,
      attributionControl: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    mapRef.current = map;

    let styleLoaded = false;
    let layersReady = false;
    let interactionsReady = false;
    let usingFallback = false;
    let tileErrors = 0;
    let styleTimeout;
    const armStyleTimeout = () => {
      window.clearTimeout(styleTimeout);
      styleTimeout = window.setTimeout(() => {
        if (styleLoaded) return;
        if (!usingFallback) {
          usingFallback = true;
          setBasemapFallback(true);
          map.setStyle(FALLBACK_STYLE);
          armStyleTimeout();
        } else {
          setFailed(true);
        }
      }, 12000);
    };
    const switchToFallback = () => {
      if (usingFallback) return;
      usingFallback = true;
      layersReady = false;
      styleLoaded = false;
      setBasemapFallback(true);
      setReady(false);
      map.setStyle(FALLBACK_STYLE);
      armStyleTimeout();
    };
    armStyleTimeout();
    const onStyleLoad = () => {
      if (layersReady) return;
      try {
        addBaseLayers(map);
        if (!interactionsReady) {
          map.on('click', 'checkpoints', (event) => {
            const props = event.features?.[0]?.properties;
            if (!props) return;
            callbacksRef.current.onSelectCheckpoint(props.routeId, props.checkpointId);
            const route = resultRef.current?.routes.find((item) => item.id === props.routeId);
            const checkpoint = route?.checkpoints.find((item) => item.id === props.checkpointId);
            if (!route || !checkpoint) return;
            popupRef.current?.remove();
            popupRef.current = new maplibregl.Popup({ closeButton: true, closeOnClick: false, maxWidth: '320px' })
              .setLngLat(event.lngLat)
              .setDOMContent(checkpointPopupContent(route, checkpoint))
              .addTo(map);
          });
          map.on('click', 'routes-line', (event) => {
            const id = event.features?.[0]?.properties?.id;
            if (id) callbacksRef.current.onSelectRoute(id);
          });
          const pointer = (layer) => {
            map.on('mouseenter', layer, () => {
              map.getCanvas().style.cursor = 'pointer';
            });
            map.on('mouseleave', layer, () => {
              map.getCanvas().style.cursor = '';
            });
          };
          pointer('checkpoints');
          pointer('routes-line');
          interactionsReady = true;
        }
        layersReady = true;
        styleLoaded = true;
        window.clearTimeout(styleTimeout);
        setFailed(false);
        setReady(true);
        map.resize();
      } catch (error) {
        window.clearTimeout(styleTimeout);
        console.error('Unable to install route layers on the map:', error);
        setFailed(true);
      }
    };
    map.on('style.load', onStyleLoad);
    map.on('error', (event) => {
      console.warn('MapLibre reported a map resource error:', event.error);
      if (!usingFallback && event.sourceId && ++tileErrors >= 3) switchToFallback();
    });

    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => map.resize());
    resizeObserver?.observe(containerRef.current);

    return () => {
      window.clearTimeout(styleTimeout);
      resizeObserver?.disconnect();
      popupRef.current?.remove();
      popupRef.current = null;
      map.remove();
      mapRef.current = null;
      fittedFor.current = null;
    };
  }, [hasResult, retryToken]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !result) return;

    const hidden = view.hiddenRouteIds;
    map.getSource('routes')?.setData(routeCollection(result.routes, view.selectedRouteId, hidden));
    map.getSource('checkpoints')?.setData(
      checkpointCollection(result.routes, view.selectedRouteId, hidden, view.selectedCheckpoint),
    );
    map.getSource('ends')?.setData(endpoints(result));
    map.getSource('corridor')?.setData(
      view.heatmapOn ? corridorFeatures(result.corridor, view.layer, view.offset) : EMPTY,
    );

    map.setPaintProperty('corridor-heat', 'heatmap-color', view.layer === 'risk' ? RISK_COLORS : WEATHER_COLORS);
    map.setLayoutProperty('corridor-heat', 'visibility', view.heatmapOn ? 'visible' : 'none');
    map.setLayoutProperty('corridor-unknown', 'visibility', view.heatmapOn ? 'visible' : 'none');

    if (fittedFor.current !== result) {
      const bounds = routesBounds(result.routes);
      if (bounds) {
        map.fitBounds(bounds, { padding: 56, duration: 600, maxZoom: 10 });
        fittedFor.current = result;
      }
    }
  }, [ready, result, view]);

  if (!result) {
    return (
      <div className={styles.placeholder} aria-busy={loading || undefined}>
        {loading ? (
          <>
            <Spinner size={28} label="Preparing map" />
            <p>Map loads after routes are found.</p>
          </>
        ) : (
          <p>No map yet.</p>
        )}
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.canvas} role="application" aria-label="Route map" />
      {!ready && !failed && (
        <div className={styles.overlay} role="status" aria-live="polite">
          <Spinner size={28} label="Loading map" />
          <p>Loading map style…</p>
        </div>
      )}
      {failed && (
        <div className={styles.overlay} role="alert">
          <p>The map could not be initialized. Route cards still work.</p>
          <Button onClick={() => setRetryToken((value) => value + 1)}>Retry map</Button>
        </div>
      )}
      {ready && basemapFallback && (
        <div className={styles.mapNotice} role="status" aria-live="polite">
          OpenFreeMap is unavailable; showing the route over the fallback map.
        </div>
      )}
    </div>
  );
}
