import { useTripAnalysis } from '../../context/TripAnalysisContext';
import { draftDiffers } from '../../utils/draft';
import AppHeader from '../AppHeader';
import StatusMessage from '../common/StatusMessage';
import TripForm from '../TripForm';
import styles from './TripTopBar.module.css';

/** Persistent results-stage bar. Edits are drafts; nothing changes until Re-analyze is clicked. */
export default function TripTopBar() {
  const { state, setDraftField, submit } = useTripAnalysis();
  const busy = state.status === 'loading' || state.status === 'restarting';
  const differs = draftDiffers(state.draft, state.resultInputs);

  return (
    <div className={styles.bar}>
      <div className={styles.brand}>
        <AppHeader compact />
      </div>
      <div className={styles.form}>
        <TripForm
          idPrefix="bar"
          layout="inline"
          values={state.draft}
          onChange={setDraftField}
          onSubmit={() => submit(state.draft)}
          submitLabel={busy ? 'Re-analyze (replaces current)' : 'Re-analyze'}
          serverErrors={state.error?.fields}
        />
      </div>
      <div className={styles.status} aria-live="polite">
        {state.status === 'restarting' && <StatusMessage variant="info">Restarting analysis…</StatusMessage>}
        {differs && state.status !== 'restarting' && (
          <StatusMessage variant="warning">
            Draft changes are not applied yet. Results below match the previous trip. Click Re-analyze to update.
          </StatusMessage>
        )}
      </div>
    </div>
  );
}
