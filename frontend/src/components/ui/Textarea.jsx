import { forwardRef } from 'react';

import { controlClass } from './Input';

export const Textarea = forwardRef(function Textarea(
  { className = '', error = false, rows = 4, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={`${controlClass(error)} leading-relaxed ${className}`}
      {...props}
    />
  );
});
