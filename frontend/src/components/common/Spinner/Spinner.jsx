import styles from './Spinner.module.css';

export default function Spinner({ size = 20, label = 'Loading', decorative = false }) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size }}
      role={decorative ? undefined : 'status'}
      aria-label={decorative ? undefined : label}
      aria-hidden={decorative || undefined}
    />
  );
}
