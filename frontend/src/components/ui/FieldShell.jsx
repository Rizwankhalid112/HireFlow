export function FieldShell({ id, label, error, hint, children, className = '' }) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      {label ? (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
          {label}
        </label>
      ) : null}
      {children}
      {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
      {!error && hint ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
}
