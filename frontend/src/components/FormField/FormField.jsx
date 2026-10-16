import styles from './FormField.module.css';

/** Visible label + control + inline error (linked with aria-describedby by the caller). */
export default function FormField({ id, label, error, hint, children }) {
  return (
    <div className={`${styles.field} ${error ? styles.invalid : ''}`}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && !error && (
        <p className={styles.hint} id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className={styles.error} id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
