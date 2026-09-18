import { forwardRef } from 'react';

export const Checkbox = forwardRef(function Checkbox({ className = '', label, id, ...props }, ref) {
  return (
    <label htmlFor={id} className={`inline-flex cursor-pointer items-center gap-2 text-[13px] text-ink ${className}`}>
      <input
        ref={ref}
        id={id}
        type="checkbox"
        className="size-3.5 cursor-pointer rounded border-line-strong text-accent accent-[var(--accent)]"
        {...props}
      />
      {label}
    </label>
  );
});
