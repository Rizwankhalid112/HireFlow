import { FieldShell } from './FieldShell';
import { Input } from './Input';

export function FormField({
  id,
  label,
  type = 'text',
  error,
  hint,
  registration,
  placeholder,
  autoComplete,
  className,
  ...rest
}) {
  return (
    <FieldShell id={id} label={label} error={error} hint={hint} className={className}>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        error={Boolean(error)}
        {...rest}
        {...registration}
      />
    </FieldShell>
  );
}
