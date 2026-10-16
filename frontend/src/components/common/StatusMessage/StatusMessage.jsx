import styles from './StatusMessage.module.css';

const ICONS = { info: 'i', warning: '!', error: '!', success: '✓' };

/** Inline, non-blocking message. Errors use role="alert", everything else a polite live region. */
export default function StatusMessage({ variant = 'info', title, children, action }) {
  return (
    <div
      className={`${styles.message} ${styles[variant]}`}
      role={variant === 'error' ? 'alert' : 'status'}
      aria-live={variant === 'error' ? 'assertive' : 'polite'}
    >
      <span className={styles.icon} aria-hidden="true">
        {ICONS[variant]}
      </span>
      <div className={styles.body}>
        {title && <strong className={styles.title}>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
