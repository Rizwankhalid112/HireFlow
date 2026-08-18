import { forwardRef } from 'react';

export const Checkbox = forwardRef(function Checkbox(
  { className = '', label, id, ...props },
  ref,
) {
  return (
    <label
      htmlFor={id}
      className={`inline-flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200 ${className}`}
    >
      <input
        ref={ref}
        id={id}
        type="checkbox"
        className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-2 focus:ring-indigo-200 dark:border-slate-600 dark:bg-slate-900"
        {...props}
      />
      {label}
    </label>
  );
});
