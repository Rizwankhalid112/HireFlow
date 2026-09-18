import { forwardRef } from 'react';

import { controlClass } from './Input';

export const Select = forwardRef(function Select(
  { className = '', error = false, options = [], placeholder, children, ...props },
  ref,
) {
  return (
    <select ref={ref} className={`${controlClass(error)} cursor-pointer pr-8 ${className}`} {...props}>
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
