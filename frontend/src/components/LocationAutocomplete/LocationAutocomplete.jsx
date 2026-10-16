import { useEffect, useId, useRef, useState } from 'react';
import { GEOCODE_MIN_CHARS } from '../../config/constants';
import { useLocationSearch } from '../../hooks/useLocationSearch';
import Spinner from '../common/Spinner';
import styles from './LocationAutocomplete.module.css';

/**
 * Accessible combobox. A location only counts as chosen once the user picks a
 * suggestion; editing the text afterwards clears the selection.
 */
export default function LocationAutocomplete({ id, selected, onSelect, onBlur, describedBy, invalid, placeholder }) {
  const listId = useId();
  const wrapperRef = useRef(null);
  const [text, setText] = useState(selected?.label || '');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  // Keep the text in sync when the selection changes from outside (e.g. a reset).
  useEffect(() => {
    if (selected) setText(selected.label);
  }, [selected]);

  const search = useLocationSearch(text, !selected);
  const showList = open && !selected && text.trim().length >= GEOCODE_MIN_CHARS;

  useEffect(() => {
    const onPointerDown = (event) => {
      if (!wrapperRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, []);

  const choose = (item) => {
    onSelect({ label: item.label, latitude: item.latitude, longitude: item.longitude });
    setText(item.label);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleChange = (event) => {
    setText(event.target.value);
    setOpen(true);
    setActiveIndex(-1);
    if (selected) onSelect(null); // editing invalidates the previous selection
  };

  const handleKeyDown = (event) => {
    const count = search.results.length;
    if (event.key === 'ArrowDown' && count) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((i) => (i + 1) % count);
    } else if (event.key === 'ArrowUp' && count) {
      event.preventDefault();
      setActiveIndex((i) => (i <= 0 ? count - 1 : i - 1));
    } else if (event.key === 'Enter' && showList && activeIndex >= 0) {
      event.preventDefault();
      choose(search.results[activeIndex]);
    } else if (event.key === 'Escape') {
      setOpen(false);
    }
  };

  const status = search.status;
  const message =
    status === 'loading'
      ? 'Searching locations…'
      : status === 'error'
        ? null
        : status === 'success' && search.results.length === 0
          ? 'No matching places. Try a city, address or postal code.'
          : null;

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <input
        id={id}
        className={`control ${styles.input} ${selected ? styles.selected : ''}`}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
        aria-describedby={describedBy}
        aria-invalid={invalid || undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        value={text}
        onChange={handleChange}
        onFocus={() => setOpen(true)}
        onBlur={onBlur}
        onKeyDown={handleKeyDown}
      />
      {status === 'loading' && !selected && (
        <span className={styles.spinner}>
          <Spinner size={16} label="Searching locations" />
        </span>
      )}
      {selected && (
        <span className={styles.check} title="Location selected">
          <span aria-hidden="true">✓</span>
          <span className="visually-hidden">Location selected</span>
        </span>
      )}

      {showList && (
        <div className={styles.popup}>
          {search.results.length > 0 && (
            <ul id={listId} role="listbox" className={styles.list} aria-label="Location suggestions">
              {search.results.map((item, index) => (
                <li
                  key={`${item.latitude},${item.longitude},${item.label}`}
                  id={`${listId}-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={`${styles.option} ${index === activeIndex ? styles.active : ''}`}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(item)}
                >
                  <span className={styles.name}>{item.name}</span>
                  <span className={styles.detail}>{[item.region, item.country].filter(Boolean).join(', ')}</span>
                </li>
              ))}
            </ul>
          )}
          {message && (
            <p className={styles.note} role="status">
              {message}
            </p>
          )}
          {status === 'error' && (
            <div className={styles.errorRow} role="alert">
              <span>{search.error?.message || 'Location search failed.'}</span>
              <button type="button" className={styles.retry} onClick={search.retry}>
                Retry
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
