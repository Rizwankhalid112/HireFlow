import { Input } from './Input';

export function FormField({
  id,
  label,
  type = 'text',
  error,
  registration,
  placeholder,
  autoComplete,
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        error={Boolean(error)}
        {...registration}
      />
      {error ? <p className="text-sm text-red-600">{error.message}</p> : null}
    </div>
  );
}
