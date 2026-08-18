import { useCallback, useEffect, useRef, useState } from 'react';

const IDLE_INTERVAL_MS = 30000;

function backupKey(sectionName) {
  return `cv_backup_${sectionName}`;
}

export function readBackup(sectionName) {
  try {
    const raw = sessionStorage.getItem(backupKey(sectionName));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearBackup(sectionName) {
  try {
    sessionStorage.removeItem(backupKey(sectionName));
  } catch {
    // ignore
  }
}

/*
 * Autosave for the CV profile (spec §10.2). Saves on tab blur and on a 30s idle
 * timer, and only ever when the form is dirty. A failed save writes the payload
 * to sessionStorage so a refresh can recover it.
 *
 * Only the profile is autosaved — child sections use explicit PUT because the
 * backend exposes no PATCH for them.
 */
export function useAutosave({ sectionName, getPayload, save, canSave, enabled = true }) {
  const [isDirty, setIsDirty] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | saving | saved | error
  const [lastSavedAt, setLastSavedAt] = useState(null);

  const inFlightRef = useRef(false);
  // Latest values are held in refs so the flush callback stays stable and the
  // event listeners never need to be re-bound.
  const dirtyRef = useRef(false);
  const payloadRef = useRef(getPayload);
  const saveRef = useRef(save);
  const canSaveRef = useRef(canSave);

  useEffect(() => {
    payloadRef.current = getPayload;
    saveRef.current = save;
    canSaveRef.current = canSave;
  }, [getPayload, save, canSave]);

  const markDirty = useCallback(() => {
    dirtyRef.current = true;
    setIsDirty(true);
  }, []);

  const flush = useCallback(async () => {
    if (!enabled || !dirtyRef.current || inFlightRef.current) {
      return;
    }

    const payload = payloadRef.current();

    // Hold invalid input locally rather than firing a PATCH that 400s silently.
    if (canSaveRef.current && !canSaveRef.current(payload)) {
      return;
    }

    inFlightRef.current = true;
    setStatus('saving');

    try {
      await saveRef.current(payload);
      dirtyRef.current = false;
      setIsDirty(false);
      setStatus('saved');
      setLastSavedAt(new Date());
      clearBackup(sectionName);
    } catch {
      setStatus('error');
      try {
        sessionStorage.setItem(backupKey(sectionName), JSON.stringify(payload));
      } catch {
        // storage unavailable — the in-memory form still holds the values
      }
    } finally {
      inFlightRef.current = false;
    }
  }, [enabled, sectionName]);

  // Trigger: tab loses focus.
  useEffect(() => {
    if (!enabled) return undefined;

    const onVisibilityChange = () => {
      if (document.hidden) {
        flush();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [enabled, flush]);

  // Trigger: 30-second idle timer.
  useEffect(() => {
    if (!enabled) return undefined;

    const timer = setInterval(() => {
      if (dirtyRef.current) {
        flush();
      }
    }, IDLE_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [enabled, flush]);

  // A PATCH cannot be relied on during unload, so warn instead.
  useEffect(() => {
    if (!enabled) return undefined;

    const onBeforeUnload = (event) => {
      if (dirtyRef.current) {
        event.preventDefault();
        event.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [enabled]);

  return { isDirty, status, lastSavedAt, markDirty, flush };
}
