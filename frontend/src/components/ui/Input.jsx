import { forwardRef } from 'react';

export const Input = forwardRef(function Input(
  { className = '', error = false, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition-colors placeholder:text-slate-400 focus:outline-none focus:ring-2 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 ${
        error
          ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
          : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-200 dark:border-slate-700'
      } ${className}`}
      {...props}
    />
  );
});
