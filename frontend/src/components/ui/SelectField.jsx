import { FieldShell } from './FieldShell';
import { Select } from './Select';

export function SelectField({
  id,
  label,
  error,
  hint,
  registration,
  options,
  placeholder,
  className,
  ...rest
}) {
  return (
    <FieldShell id={id} label={label} error={error} hint={hint} className={className}>
      <Select
        id={id}
        options={options}
        placeholder={placeholder}
        error={Boolean(error)}
        {...rest}
        {...registration}
      />
    </FieldShell>
  );
}
