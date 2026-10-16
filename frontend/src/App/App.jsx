import { TripAnalysisProvider, useTripAnalysis } from '../context/TripAnalysisContext';
import ErrorBoundary from '../components/common/ErrorBoundary';
import Button from '../components/common/Button';
import ResultsPage from '../pages/ResultsPage';
import SetupPage from '../pages/SetupPage';
import styles from './App.module.css';

function StageSwitch() {
  const { state } = useTripAnalysis();
  return state.stage === 'results' ? <ResultsPage /> : <SetupPage />;
}

function FatalFallback() {
  return (
    <div className={styles.fatal} role="alert">
      <h1>Something went wrong</h1>
      <p>The app hit an unexpected problem. Reloading usually fixes it.</p>
      <Button onClick={() => window.location.reload()}>Reload the app</Button>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary name="app" fallback={<FatalFallback />}>
      <TripAnalysisProvider>
        <StageSwitch />
      </TripAnalysisProvider>
    </ErrorBoundary>
  );
}
