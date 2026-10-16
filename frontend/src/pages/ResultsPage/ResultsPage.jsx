import { useEffect, useState } from 'react';
import { useTripAnalysis } from '../../context/TripAnalysisContext';
import { useResultsView } from '../../hooks/useResultsView';
import { formatDateTime, formatWeight } from '../../utils/formatters';
import Button from '../../components/common/Button';
import ErrorBoundary from '../../components/common/ErrorBoundary';
import ErrorPanel from '../../components/common/ErrorPanel';
import StatusMessage from '../../components/common/StatusMessage';
import TripTopBar from '../../components/TripTopBar';
import RouteCardList from '../../components/RouteCardList';
import CheckpointPanel from '../../components/CheckpointPanel';
import TripMap from '../../components/TripMap';
import ForecastControls from '../../components/ForecastControls';
import styles from './ResultsPage.module.css';

const PROGRESS = [
  'Finding routes…',
  'Checking weather along each route…',
  'Calculating risk and ranking alternatives…',
];

function ProgressCopy({ status }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (status !== 'loading' && status !== 'restarting') return undefined;
    setStep(0);
    const timer = window.setInterval(() => setStep((current) => (current + 1) % PROGRESS.length), 2800);
    return () => window.clearInterval(timer);
  }, [status]);
  return PROGRESS[step];
}

function findCheckpoint(routes, selection) {
  if (!selection) return null;
  const route = routes.find((item) => item.id === selection.routeId);
  const checkpoint = route?.checkpoints.find((item) => item.id === selection.checkpointId);
  return route && checkpoint ? { route, checkpoint } : null;
}

function ResultsFallback({ reset, title, message }) {
  return <ErrorPanel title={title} message={message} onRetry={reset} retryLabel="Reload this panel" />;
}

export default function ResultsPage() {
  const { state, retry, returnToSetup } = useTripAnalysis();
  const result = state.result;
  const { view, selectRoute, toggleRouteVisible, selectCheckpoint, setLayer, setHeatmapOn, setOffset } =
    useResultsView(result);
  const busy = state.status === 'loading' || state.status === 'restarting';
  const inspected = result ? findCheckpoint(result.routes, view.selectedCheckpoint) : null;
  const selectedRoute = result?.routes.find((route) => route.id === view.selectedRouteId) || result?.routes[0];

  return (
    <div className={styles.page}>
      <TripTopBar />
      <div className={styles.workspace}>
        <aside className={styles.sidebar} aria-label="Route comparison">
          <ErrorBoundary
            name="route results"
            resetKey={state.resultId}
            fallback={({ reset }) => (
              <ResultsFallback
                reset={reset}
                title="Route comparison unavailable"
                message="The route list could not be displayed. The map may still work."
              />
            )}
          >
            <ResultsSidebar
              state={state}
              result={result}
              view={view}
              busy={busy}
              selectedRoute={selectedRoute}
              inspected={inspected}
              onRetry={retry}
              onReturnToSetup={returnToSetup}
              onSelectRoute={selectRoute}
              onToggleVisible={toggleRouteVisible}
              onSelectCheckpoint={selectCheckpoint}
            />
          </ErrorBoundary>
        </aside>

        <section className={styles.mapColumn} aria-label="Trip map">
          <ErrorBoundary
            name="map"
            resetKey={state.resultId}
            fallback={({ reset }) => (
              <ResultsFallback
                reset={reset}
                title="Map unavailable"
                message="The map could not be displayed. Route cards and the recommendation are still available in the left panel."
              />
            )}
          >
            <TripMap
              result={result}
              view={view}
              loading={busy && !result}
              onSelectRoute={selectRoute}
              onSelectCheckpoint={selectCheckpoint}
            />
          </ErrorBoundary>
          <ErrorBoundary
            name="forecast overlay"
            resetKey={state.resultId}
            fallback={({ reset }) => (
              <ResultsFallback
                reset={reset}
                title="Forecast controls unavailable"
                message="The heatmap slider failed. Routes and checkpoints are still usable."
              />
            )}
          >
            {result && (
              <ForecastControls
                corridor={result.corridor}
                forecast={result.forecast}
                layer={view.layer}
                heatmapOn={view.heatmapOn}
                offset={view.offset}
                onLayer={setLayer}
                onHeatmapOn={setHeatmapOn}
                onOffset={setOffset}
              />
            )}
          </ErrorBoundary>
        </section>
      </div>
    </div>
  );
}

function ResultsSidebar({
  state,
  result,
  view,
  busy,
  selectedRoute,
  inspected,
  onRetry,
  onReturnToSetup,
  onSelectRoute,
  onToggleVisible,
  onSelectCheckpoint,
}) {
  return (
    <>
      {busy && (
        <StatusMessage variant="info" title={state.status === 'restarting' ? 'Restarting analysis' : 'Analyzing trip'}>
          <ProgressCopy status={state.status} />
        </StatusMessage>
      )}

      {state.error && (
        <StatusMessage
          variant="error"
          title={result ? 'The latest re-analysis failed' : 'Analysis failed'}
          action={
            <Button variant="secondary" onClick={onRetry}>
              Retry
            </Button>
          }
        >
          {state.error.message}
        </StatusMessage>
      )}

      {result && (busy || state.error) && (
        <StatusMessage variant="warning">
          Showing the previous analysis
          {result.trip?.origin?.label ? ` for ${result.trip.origin.label} → ${result.trip.destination.label}` : ''}.
          New results will replace this when the request succeeds.
        </StatusMessage>
      )}

      {result?.warnings?.length > 0 && !busy && (
        <ul className={styles.warnings}>
          {result.warnings.map((warning) => (
            <li key={`${warning.code}-${warning.route_id || ''}-${warning.message}`}>
              <StatusMessage variant={warning.code === 'NO_SAFE_ROUTE' ? 'error' : 'warning'} title={warning.code.replaceAll('_', ' ')}>
                {warning.message}
              </StatusMessage>
            </li>
          ))}
        </ul>
      )}

      {!result && !busy && state.error && (
        <ErrorPanel
          title="No routes to show"
          message={state.error.message}
          onRetry={onRetry}
          secondary={
            <Button variant="ghost" onClick={onReturnToSetup}>
              Edit trip
            </Button>
          }
        />
      )}

      {!result && busy && <RouteCardList routes={[]} loading />}

      {result && result.routes.length === 0 && (
        <ErrorPanel
          title="No route was returned"
          message="The routing provider did not find a path between these places. Try a nearby address."
          onRetry={onReturnToSetup}
          retryLabel="Edit trip"
        />
      )}

      {result && result.routes.length > 0 && (
        <>
          <RecommendationBanner recommendation={result.recommendation} trip={result.trip} />
          <div className={styles.routeListHeader}>
            <h2>Route options</h2>
            <span>
              Showing {result.routes.length} of up to 3 routes
            </span>
          </div>
          <RouteCardList
            routes={result.routes}
            recommendation={result.recommendation}
            selectedRouteId={view.selectedRouteId}
            hiddenRouteIds={view.hiddenRouteIds}
            onSelect={onSelectRoute}
            onToggleVisible={onToggleVisible}
          />
          <CheckpointPanel
            route={selectedRoute}
            inspected={inspected}
            onSelectCheckpoint={(checkpointId) => onSelectCheckpoint(selectedRoute?.id, checkpointId)}
          />
        </>
      )}
    </>
  );
}

function RecommendationBanner({ recommendation, trip }) {
  if (!recommendation) return null;
  const unsafe = recommendation.all_routes_unsafe;
  return (
    <StatusMessage
      variant={unsafe ? 'error' : recommendation.incomplete ? 'warning' : 'success'}
      title={unsafe ? 'No fully safe route' : 'Recommended route'}
    >
      <p>{recommendation.summary}</p>
      <p className={styles.tripMeta}>
        Depart {formatDateTime(trip.departure_at)} · {formatWeight(trip.load_weight_lb)} · checkpoints every{' '}
        {trip.checkpoint_interval_miles} mi
      </p>
    </StatusMessage>
  );
}
