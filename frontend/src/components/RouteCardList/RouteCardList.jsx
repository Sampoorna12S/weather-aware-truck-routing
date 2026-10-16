import { formatDateTime, formatDuration, formatMiles, formatScore } from '../../utils/formatters';
import { routeStyle } from '../../utils/routeStyle';
import RiskBadge from '../common/RiskBadge';
import Skeleton from '../common/Skeleton';
import styles from './RouteCardList.module.css';

function worstShown(summary) {
  if (summary.no_travel) return 'NO_TRAVEL';
  if (summary.severe_miles > 0) return 'SEVERE';
  if (summary.high_miles > 0) return 'HIGH';
  if (summary.moderate_miles > 0) return 'MODERATE';
  if (summary.unknown_miles > 0 && !(summary.low_miles > 0)) return 'UNKNOWN';
  return 'LOW';
}

export default function RouteCardList({
  routes,
  recommendation,
  selectedRouteId,
  hiddenRouteIds,
  onSelect,
  onToggleVisible,
  loading = false,
}) {
  if (loading) {
    return (
      <div className={styles.list} aria-busy="true" aria-label="Loading routes">
        {[0, 1, 2].map((index) => (
          <div key={index} className={styles.skeletonCard}>
            <Skeleton height={18} width="40%" />
            <Skeleton height={12} width="70%" />
            <Skeleton height={12} width="55%" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {routes.map((route) => {
        const selected = route.id === selectedRouteId;
        const hidden = hiddenRouteIds.includes(route.id);
        const style = routeStyle(route);
        const recommended = route.is_recommended && !recommendation?.all_routes_unsafe;
        return (
          <li key={route.id}>
            <article
              className={`${styles.card} ${selected ? styles.selected : ''} ${hidden ? styles.hidden : ''}`}
              style={{ '--route-color': style.color }}
            >
              <button type="button" className={styles.select} onClick={() => onSelect(route.id)} aria-pressed={selected}>
                <header className={styles.header}>
                  <span className={styles.swatch} aria-hidden="true" />
                  <h3 className={styles.title}>{route.label}</h3>
                  {recommended && <span className={styles.rec}>Recommended</span>}
                  {route.risk_summary.no_travel && <RiskBadge level="NO_TRAVEL" />}
                  {!route.risk_summary.no_travel && <RiskBadge level={worstShown(route.risk_summary)} />}
                </header>
                <dl className={styles.stats}>
                  <div>
                    <dt>Distance</dt>
                    <dd>{formatMiles(route.distance_miles)}</dd>
                  </div>
                  <div>
                    <dt>Duration</dt>
                    <dd>{formatDuration(route.duration_seconds)}</dd>
                  </div>
                  <div>
                    <dt>Arrival</dt>
                    <dd>{formatDateTime(route.eta)}</dd>
                  </div>
                  <div>
                    <dt>Severe mi</dt>
                    <dd>{route.risk_summary.severe_miles}</dd>
                  </div>
                  <div>
                    <dt>High mi</dt>
                    <dd>{route.risk_summary.high_miles}</dd>
                  </div>
                  <div>
                    <dt>Avg risk</dt>
                    <dd>{formatScore(route.risk_summary.average_risk_score)}</dd>
                  </div>
                </dl>
                <p className={styles.why}>{route.explanation}</p>
              </button>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={!hidden}
                  onChange={() => onToggleVisible(route.id)}
                />
                Show on map
              </label>
            </article>
          </li>
        );
      })}
    </ul>
  );
}
