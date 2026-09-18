import { FieldShell } from './FieldShell';
import { Textarea } from './Textarea';

export function TextareaField({ id, label, error, hint, registration, rows, className, ...rest }) {
  return (
    <FieldShell id={id} label={label} error={error} hint={hint} className={className}>
      <Textarea id={id} rows={rows} error={Boolean(error)} {...rest} {...registration} />
    </FieldShell>
  );
}
