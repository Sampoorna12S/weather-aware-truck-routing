import { useTripAnalysis } from '../../context/TripAnalysisContext';
import AppHeader from '../../components/AppHeader';
import StatusMessage from '../../components/common/StatusMessage';
import TripForm from '../../components/TripForm';
import styles from './SetupPage.module.css';

const STEPS = [
  ['Find routes', 'Up to three alternatives between your origin and destination.'],
  ['Check weather', 'Hourly wind, rain and snow forecasts at each checkpoint, timed to when you will be there.'],
  ['Compare risk', 'Load-aware risk levels, with the best route recommended by safety first.'],
];

/** Stage 1: introduction and trip form only. No map, routes or forecast controls here. */
export default function SetupPage() {
  const { state, setDraftField, submit } = useTripAnalysis();

  return (
    <main className={styles.page}>
      <AppHeader />
      <section className={styles.card} aria-labelledby="setup-heading">
        <h2 id="setup-heading" className={styles.heading}>
          Plan your trip
        </h2>
        <p className={styles.lead}>Enter the trip details below. We will compare routes and weather along each one.</p>
        {state.error && state.stage === 'setup' && (
          <StatusMessage variant="error" title="The last analysis failed">
            {state.error.message}
          </StatusMessage>
        )}
        <TripForm
          idPrefix="setup"
          values={state.draft}
          onChange={setDraftField}
          onSubmit={() => submit(state.draft)}
          submitLabel="Analyze routes"
          serverErrors={state.error?.fields}
        />
      </section>

      <ol className={styles.steps} aria-label="How it works">
        {STEPS.map(([title, text], index) => (
          <li key={title} className={styles.step}>
            <span className={styles.number} aria-hidden="true">
              {index + 1}
            </span>
            <div>
              <strong>{title}</strong>
              <p>{text}</p>
            </div>
          </li>
        ))}
      </ol>
    </main>
  );
}
