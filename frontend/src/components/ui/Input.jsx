import { forwardRef } from 'react';

/* One control skin, shared by Input / Select / Textarea so the three never
   drift apart. Exported because a few call sites style a div to match. */
export const controlClass = (error) =>
  `w-full rounded-control border bg-surface px-2.5 py-1.5 text-[13px] text-ink shadow-card transition-colors placeholder:text-subtle ${
    error
      ? 'border-bad focus:border-bad focus:ring-2 focus:ring-bad/20'
      : 'border-line-strong focus:border-accent focus:ring-2 focus:ring-accent/20'
  } focus:outline-none disabled:opacity-50`;

export const Input = forwardRef(function Input({ className = '', error = false, ...props }, ref) {
  return <input ref={ref} className={`${controlClass(error)} ${className}`} {...props} />;
});
