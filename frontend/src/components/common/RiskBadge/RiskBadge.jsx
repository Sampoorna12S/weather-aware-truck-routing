import { RISK_META } from '../../../config/constants';
import styles from './RiskBadge.module.css';

/** Colour + symbol + text, so risk is never conveyed by colour alone. */
export default function RiskBadge({ level, compact = false, subLabel= "Risk" }) {
  const meta = RISK_META[level] || RISK_META.UNKNOWN;
  return (
    <span
      className={`${styles.badge} ${compact ? styles.compact : ''} ${styles[level] || styles.UNKNOWN}`}
      title={`${meta.label}`}
      aria-label={`${meta.label}`}
    >
      {/* <span className={styles.prefix} aria-hidden="true">Risk:</span> */}
      <span className={styles.symbol} aria-hidden="true">
        {meta.symbol}
      </span>
      {!compact && <span>{meta.label+ ` ${subLabel}`}</span>}
    </span>
  );
}
