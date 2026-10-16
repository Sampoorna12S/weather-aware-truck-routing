import { Component } from 'react';
import Button from '../Button';
import styles from './ErrorBoundary.module.css';

/**
 * Catches render-time errors only (async errors are handled with try/catch and request state).
 * `fallback` may be a node or a function `({ reset }) => node` for area-specific fallbacks.
 * Diagnostic details go to the console; users only see a non-technical message.
 */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error(`[ErrorBoundary:${this.props.name || 'app'}]`, error, info?.componentStack);
  }

  componentDidUpdate(previousProps) {
    if (this.state.error && previousProps.resetKey !== this.props.resetKey) this.reset();
  }

  reset = () => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  render() {
    if (!this.state.error) return this.props.children;
    const { fallback, name } = this.props;
    if (typeof fallback === 'function') return fallback({ reset: this.reset });
    if (fallback) return fallback;
    return (
      <div className={styles.fallback} role="alert">
        <h2>Something went wrong{name ? ` in ${name}` : ''}</h2>
        <p>This part of the page could not be displayed. Your trip details are safe.</p>
        <Button onClick={this.reset}>Try again</Button>
      </div>
    );
  }
}
