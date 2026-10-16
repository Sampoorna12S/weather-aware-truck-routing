import { formatDateTime, formatMilesPrecise, formatWeatherValue } from '../../utils/formatters';
import RiskBadge from '../common/RiskBadge';
import styles from './CheckpointPanel.module.css';

export default function CheckpointPanel({ route, inspected, onSelectCheckpoint }) {
  if (!route) return null;
  const checkpoint = inspected?.checkpoint;

  return (
    <section className={styles.panel} aria-label="Checkpoints">
      <h3 className={styles.heading}>{route.label} checkpoints</h3>
      <p className={styles.hint}>
        Each marker is miles along this route. L = Low, M = Moderate; select any marker to inspect it. Risk uses the truck&apos;s estimated arrival, not the heatmap slider.
      </p>
      <div className={styles.chips} role="list">
        {route.checkpoints.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${styles.chip} ${checkpoint?.id === item.id ? styles.active : ''}`}
            onClick={() => onSelectCheckpoint(item.id)}
            aria-pressed={checkpoint?.id === item.id}
          >
            <RiskBadge level={item.overall_risk} compact />
            <span>{formatMilesPrecise(item.distance_along_route_miles)}</span>
          </button>
        ))}
      </div>

      {checkpoint ? (
        <dl className={styles.detail}>
          <div>
            <dt>Distance along route</dt>
            <dd>{formatMilesPrecise(checkpoint.distance_along_route_miles)}</dd>
          </div>
          <div>
            <dt>Estimated arrival</dt>
            <dd>{formatDateTime(checkpoint.eta)}</dd>
          </div>
          <div>
            <dt>Forecast hour used</dt>
            <dd>{checkpoint.weather?.forecast_time ? formatDateTime(checkpoint.weather.forecast_time) : 'unavailable'}</dd>
          </div>
          <div>
            <dt>Wind</dt>
            <dd>
              {formatWeatherValue(checkpoint.weather?.wind_mph, 'mph')} <RiskBadge level={checkpoint.condition_risks.wind} compact />
            </dd>
          </div>
          <div>
            <dt>Rain</dt>
            <dd>
              {formatWeatherValue(checkpoint.weather?.rain_inches_per_hour, 'in/hr', 2)}{' '}
              <RiskBadge level={checkpoint.condition_risks.rain} compact />
            </dd>
          </div>
          <div>
            <dt>Snow</dt>
            <dd>
              {formatWeatherValue(checkpoint.weather?.snow_inches_per_hour, 'in/hr', 2)}{' '}
              <RiskBadge level={checkpoint.condition_risks.snow} compact />
            </dd>
          </div>
          <div>
            <dt>Overall</dt>
            <dd>
              <RiskBadge level={checkpoint.overall_risk} />
              {checkpoint.data_status !== 'AVAILABLE' && <span className={styles.status}>Unavailable</span>}
            </dd>
          </div>
        </dl>
      ) : (
        <p className={styles.hint}>Select a checkpoint on the map or in the list for wind, rain, snow and ETA.</p>
      )}
    </section>
  );
}
