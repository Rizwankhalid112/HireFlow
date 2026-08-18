import { forwardRef } from 'react';

export const Select = forwardRef(function Select(
  { className = '', error = false, options = [], placeholder, children, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors focus:outline-none focus:ring-2 dark:bg-slate-900 dark:text-slate-100 ${
        error
          ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
          : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-200 dark:border-slate-700'
      } ${className}`}
      {...props}
    >
      {placeholder ? <option value="">{placeholder}</option> : null}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
      {children}
    </select>
  );
});
