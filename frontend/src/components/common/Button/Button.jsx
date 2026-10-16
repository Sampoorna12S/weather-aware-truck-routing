import Spinner from '../Spinner';
import styles from './Button.module.css';

export default function Button({ variant = 'primary', loading = false, disabled = false, children, className = '', ...rest }) {
  const classes = [styles.button, styles[variant], className].filter(Boolean).join(' ');
  return (
    <button type="button" className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading && <Spinner size={14} decorative />}
      <span>{children}</span>
    </button>
  );
}
