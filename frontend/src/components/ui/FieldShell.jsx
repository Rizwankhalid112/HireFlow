export function FieldShell({ id, label, error, hint, children, className = '' }) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label ? (
        <label htmlFor={id} className="text-xs font-medium text-ink">
          {label}
        </label>
      ) : null}
      {children}
      {error ? (
        <p className="text-[11px] text-bad">{error.message}</p>
      ) : hint ? (
        <p className="text-[11px] text-subtle">{hint}</p>
      ) : null}
    </div>
  );
}
