import styles from './AppHeader.module.css';

export default function AppHeader({ compact = false }) {
  return (
    <header className={`${styles.header} ${compact ? styles.compact : ''}`}>
      <span className={styles.logo} aria-hidden="true">
        🚚
      </span>
      <div>
        <h1 className={styles.title}>Weather-Aware Truck Routing</h1>
        {!compact && <p className={styles.subtitle}>Compare route options by weather risk, load weight and travel time.</p>}
      </div>
    </header>
  );
}
