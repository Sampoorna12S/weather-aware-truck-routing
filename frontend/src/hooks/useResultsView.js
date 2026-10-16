import { useCallback, useState } from 'react';

const initialView = (result) => ({
  selectedRouteId: result ? result.recommendation?.route_id || result.routes[0]?.id || null : null,
  hiddenRouteIds: [],
  selectedCheckpoint: null, // { routeId, checkpointId }
  layer: 'risk',
  heatmapOn: true,
  offset: 0,
});

/**
 * UI-only view state for one result: which route is highlighted, which are hidden,
 * the inspected checkpoint and the heatmap controls. It resets whenever a new result arrives.
 */
export function useResultsView(result) {
  const [view, setView] = useState(() => initialView(result));
  const [seenResult, setSeenResult] = useState(result);
  if (result !== seenResult) {
    setSeenResult(result);
    setView(initialView(result));
  }

  const patch = useCallback((changes) => setView((previous) => ({ ...previous, ...changes })), []);

  return {
    view,
    selectRoute: useCallback((routeId) => patch({ selectedRouteId: routeId, selectedCheckpoint: null }), [patch]),
    toggleRouteVisible: useCallback(
      (routeId) =>
        setView((previous) => {
          const hidden = previous.hiddenRouteIds.includes(routeId);
          return {
            ...previous,
            hiddenRouteIds: hidden
              ? previous.hiddenRouteIds.filter((id) => id !== routeId)
              : [...previous.hiddenRouteIds, routeId],
          };
        }),
      [],
    ),
    selectCheckpoint: useCallback(
      (routeId, checkpointId) =>
        setView((previous) => ({
          ...previous,
          selectedRouteId: routeId ?? previous.selectedRouteId,
          selectedCheckpoint: checkpointId ? { routeId: routeId ?? previous.selectedRouteId, checkpointId } : null,
        })),
      [],
    ),
    setLayer: useCallback((layer) => patch({ layer }), [patch]),
    setHeatmapOn: useCallback((heatmapOn) => patch({ heatmapOn }), [patch]),
    setOffset: useCallback((offset) => patch({ offset }), [patch]),
  };
}
