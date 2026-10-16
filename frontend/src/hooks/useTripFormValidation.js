import { useCallback, useMemo, useState } from 'react';
import { FIELD_LABELS, FIELD_ORDER, firstInvalidField, validateDraft } from '../utils/validation';

/**
 * Live validation for the trip form. Errors are computed on every change, but only
 * shown for fields the user has touched (or after a submit attempt), so the form
 * does not open covered in red messages. Server-side field errors are shown too.
 */
export function useTripFormValidation(values, serverErrors = {}) {
  const [touched, setTouched] = useState({});
  const errors = useMemo(() => validateDraft(values), [values]);

  const touch = useCallback((field) => setTouched((prev) => (prev[field] ? prev : { ...prev, [field]: true })), []);
  const touchAll = useCallback(() => setTouched(Object.fromEntries(FIELD_ORDER.map((f) => [f, true]))), []);

  const visibleErrors = useMemo(() => {
    const shown = {};
    for (const field of FIELD_ORDER) {
      if (errors[field]) {
        if (touched[field]) shown[field] = errors[field];
      } else if (serverErrors?.[field]) {
        shown[field] = serverErrors[field];
      }
    }
    return shown;
  }, [errors, touched, serverErrors]);

  const missing = FIELD_ORDER.filter((field) => errors[field]).map((field) => FIELD_LABELS[field]);
  return {
    errors,
    visibleErrors,
    isValid: missing.length === 0,
    missing,
    firstInvalid: firstInvalidField(errors),
    touch,
    touchAll,
  };
}
