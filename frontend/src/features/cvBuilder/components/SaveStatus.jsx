const LABELS = {
  idle: '',
  saving: 'Saving…',
  saved: 'All changes saved',
  error: 'Changes not saved — retrying',
};

const TONES = {
  saving: 'text-slate-500 dark:text-slate-400',
  saved: 'text-emerald-600 dark:text-emerald-400',
  error: 'text-red-600 dark:text-red-400',
};

export function SaveStatus({ status, lastSavedAt }) {
  if (!status || status === 'idle') {
    return null;
  }

  const time = lastSavedAt
    ? lastSavedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <p className={`text-xs font-medium ${TONES[status] ?? ''}`}>
      {LABELS[status]}
      {status === 'saved' && time ? ` · ${time}` : null}
    </p>
  );
}
