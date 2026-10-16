import Button from '../Button';
import styles from './ErrorPanel.module.css';

/** Block-level error with recovery actions, for areas that failed to load. */
export default function ErrorPanel({ title, message, onRetry, retryLabel = 'Try again', secondary }) {
  return (
    <div className={styles.panel} role="alert">
      <h2 className={styles.title}>{title}</h2>
      <p className={styles.message}>{message}</p>
      <div className={styles.actions}>
        {onRetry && <Button onClick={onRetry}>{retryLabel}</Button>}
        {secondary}
      </div>
    </div>
  );
}
