import { Icon } from './Icon';

const variants = {
  primary: 'bg-accent text-accent-on hover:bg-accent-hover shadow-card',
  secondary: 'bg-surface text-ink border border-line-strong hover:bg-surface-2',
  ghost: 'text-muted hover:bg-surface-3 hover:text-ink',
  danger: 'bg-bad-solid text-white hover:brightness-110',
  quiet: 'text-accent hover:bg-accent-soft',
};

const sizes = {
  sm: 'h-7 px-2.5 text-xs gap-1.5',
  md: 'h-8 px-3.5 text-[13px] gap-2',
  lg: 'h-10 px-5 text-sm gap-2',
};

export function Button({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  icon,
  iconAfter,
  loading = false,
  disabled,
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-control font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <span className="size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : (
        icon && <Icon name={icon} size={size === 'lg' ? 16 : 14} />
      )}
      {children}
      {iconAfter && !loading && <Icon name={iconAfter} size={size === 'lg' ? 16 : 14} />}
    </button>
  );
}

/* A square button whose only content is an icon. `label` is required — it is
   the control's entire accessible name. */
export function IconButton({
  icon,
  label,
  size = 'md',
  variant = 'ghost',
  className = '',
  ...props
}) {
  const box = size === 'sm' ? 'size-7' : 'size-8';

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex items-center justify-center rounded-control transition-colors disabled:pointer-events-none disabled:opacity-40 ${variants[variant]} ${box} ${className}`}
      {...props}
    >
      <Icon name={icon} size={15} />
    </button>
  );
}
