import { Icon } from '@/components/ui';

const STATES = {
  saving: { label: 'Saving…', tone: 'text-subtle', icon: 'refresh' },
  saved: { label: 'All changes saved', tone: 'text-ok', icon: 'check' },
  error: { label: 'Changes not saved — retrying', tone: 'text-bad', icon: 'warning' },
};

export function SaveStatus({ status, lastSavedAt }) {
  const state = STATES[status];
  if (!state) return null;

  const time =
    status === 'saved' && lastSavedAt
      ? lastSavedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : null;

  return (
    <p className={`flex items-center gap-1.5 text-[11px] font-medium ${state.tone}`}>
      <Icon name={state.icon} size={12} strokeWidth={2.2} />
      {state.label}
      {time ? ` · ${time}` : null}
    </p>
  );
}
