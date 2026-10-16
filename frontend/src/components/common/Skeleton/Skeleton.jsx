import styles from './Skeleton.module.css';

export default function Skeleton({ width = '100%', height = 14, radius, className = '' }) {
  return (
    <span
      className={`${styles.skeleton} ${className}`}
      style={{ width, height, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}
