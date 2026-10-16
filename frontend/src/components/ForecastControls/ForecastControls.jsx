import { FORECAST_MAX_HOURS, HEATMAP_LAYERS, RISK_META } from '../../config/constants';
import { formatForecastHour } from '../../utils/formatters';
import styles from './ForecastControls.module.css';

const LAYER_KEYS = Object.keys(HEATMAP_LAYERS);

export default function ForecastControls({
  corridor,
  forecast,
  layer,
  heatmapOn,
  offset,
  onLayer,
  onHeatmapOn,
  onOffset,
}) {
  const max = forecast?.offset_max_hours ?? FORECAST_MAX_HOURS;
  const timeLabel = corridor?.times_utc?.[offset] ? formatForecastHour(corridor.times_utc[offset]) : 'unavailable';
  const layerMeta = HEATMAP_LAYERS[layer];

  return (
    <div className={styles.bar}>
      <div className={styles.row}>
        <label className={styles.toggle}>
          <input type="checkbox" checked={heatmapOn} onChange={(event) => onHeatmapOn(event.target.checked)} />
          Weather overlay
        </label>
        <fieldset className={styles.layers} disabled={!heatmapOn}>
          <legend className="visually-hidden">Overlay type</legend>
          {LAYER_KEYS.map((key) => (
            <label key={key}>
              <input type="radio" name="heatmap-layer" checked={layer === key} onChange={() => onLayer(key)} />
              {HEATMAP_LAYERS[key].label}
            </label>
          ))}
        </fieldset>
      </div>

      <div className={styles.sliderBlock}>
        <label htmlFor="forecast-offset">
          Forecast +{offset}h from departure
          <span className={styles.when}> · {timeLabel}</span>
        </label>
        <input
          id="forecast-offset"
          className={styles.slider}
          type="range"
          min={forecast?.offset_min_hours ?? 0}
          max={max}
          step={1}
          value={offset}
          onChange={(event) => onOffset(Number(event.target.value))}
          disabled={!heatmapOn || !corridor}
        />
        <div className={styles.ticks} aria-hidden="true">
          <span>0h</span>
          <span>24h</span>
          <span>48h</span>
        </div>
      </div>

      <p className={styles.note}>
        Slider shows the corridor at one forecast hour. Route risk still uses each checkpoint&apos;s arrival time.
        {corridor ? ` ${layerMeta.description}${layerMeta.unit ? ` (${layerMeta.unit})` : ''}.` : ' Overlay data was not available for this trip.'}
      </p>
      <Legend layer={layer} />
    </div>
  );
}

function Legend({ layer }) {
  if (layer === 'risk') {
    return (
      <ul className={styles.legend}>
        {['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL', 'UNKNOWN'].map((level) => (
          <li key={level}>
            <span className={styles.swatch} style={{ background: RISK_META[level].color }} />
            {RISK_META[level].symbol} {RISK_META[level].label}
          </li>
        ))}
      </ul>
    );
  }
  const meta = HEATMAP_LAYERS[layer];
  return (
    <p className={styles.scale}>
      {meta.label}: 0{meta.unit && ` ${meta.unit}`} → {meta.max}
      {meta.unit && ` ${meta.unit}`}
    </p>
  );
}
