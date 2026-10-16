import { useRef } from 'react';
import { CHECKPOINT_INTERVALS, MAX_LOAD_LB } from '../../config/constants';
import { useTripFormValidation } from '../../hooks/useTripFormValidation';
import Button from '../common/Button';
import FormField from '../FormField';
import LocationAutocomplete from '../LocationAutocomplete';
import styles from './TripForm.module.css';

const describe = (id, error, hint) => [error && `${id}-error`, hint && !error && `${id}-hint`].filter(Boolean).join(' ') || undefined;

/**
 * Controlled trip form shared by the setup page (`layout="stacked"`) and the results
 * top bar (`layout="inline"`). Validates live; submit stays disabled until valid.
 */
export default function TripForm({
  idPrefix,
  values,
  onChange,
  onSubmit,
  submitLabel,
  serverErrors,
  layout = 'stacked',
  busy = false,
  children,
}) {
  const formRef = useRef(null);
  const { visibleErrors, isValid, missing, firstInvalid, touch, touchAll } = useTripFormValidation(values, serverErrors);
  const id = (field) => `${idPrefix}-${field}`;

  const handleSubmit = (event) => {
    event.preventDefault();
    touchAll();
    if (!isValid) {
      formRef.current?.querySelector(`#${id(firstInvalid)}`)?.focus();
      return;
    }
    onSubmit();
  };

  return (
    <form ref={formRef} className={`${styles.form} ${styles[layout]}`} onSubmit={handleSubmit} noValidate>
      <FormField id={id('origin')} label="Origin" error={visibleErrors.origin}>
        <LocationAutocomplete
          id={id('origin')}
          selected={values.origin}
          onSelect={(place) => onChange('origin', place)}
          onBlur={() => touch('origin')}
          describedBy={describe(id('origin'), visibleErrors.origin)}
          invalid={!!visibleErrors.origin}
          placeholder="City, address or ZIP code"
        />
      </FormField>

      <FormField id={id('destination')} label="Destination" error={visibleErrors.destination}>
        <LocationAutocomplete
          id={id('destination')}
          selected={values.destination}
          onSelect={(place) => onChange('destination', place)}
          onBlur={() => touch('destination')}
          describedBy={describe(id('destination'), visibleErrors.destination)}
          invalid={!!visibleErrors.destination}
          placeholder="City, address or ZIP code"
        />
      </FormField>

      <FormField id={id('departureAt')} label="Departure date & time" error={visibleErrors.departureAt}>
        <input
          id={id('departureAt')}
          className="control"
          type="datetime-local"
          value={values.departureAt}
          onChange={(event) => onChange('departureAt', event.target.value)}
          onBlur={() => touch('departureAt')}
          aria-invalid={!!visibleErrors.departureAt || undefined}
          aria-describedby={describe(id('departureAt'), visibleErrors.departureAt)}
        />
      </FormField>

      <FormField id={id('loadWeight')} label="Load weight (lb)" error={visibleErrors.loadWeight}>
        <input
          id={id('loadWeight')}
          className="control"
          type="number"
          inputMode="numeric"
          min="1"
          max={MAX_LOAD_LB}
          step="any"
          placeholder="e.g. 32000"
          value={values.loadWeight}
          onChange={(event) => onChange('loadWeight', event.target.value)}
          onBlur={() => touch('loadWeight')}
          aria-invalid={!!visibleErrors.loadWeight || undefined}
          aria-describedby={describe(id('loadWeight'), visibleErrors.loadWeight)}
        />
      </FormField>

      <FormField id={id('interval')} label="Checkpoint every" error={visibleErrors.interval}>
        <select
          id={id('interval')}
          className="control"
          value={values.interval}
          onChange={(event) => onChange('interval', Number(event.target.value))}
          onBlur={() => touch('interval')}
          aria-describedby={describe(id('interval'), visibleErrors.interval)}
        >
          {CHECKPOINT_INTERVALS.map((miles) => (
            <option key={miles} value={miles}>
              {miles} miles
            </option>
          ))}
        </select>
      </FormField>

      <div className={styles.actions}>
        <Button type="submit" disabled={!isValid || busy} aria-describedby={`${idPrefix}-submit-hint`}>
          {submitLabel}
        </Button>
        {children}
        <p className={styles.submitHint} id={`${idPrefix}-submit-hint`} aria-live="polite">
          {isValid ? 'Ready to analyze.' : `Still needed: ${missing.join(', ')}.`}
        </p>
      </div>
    </form>
  );
}
