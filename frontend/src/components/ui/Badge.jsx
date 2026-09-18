const variants = {
  neutral: 'border-line bg-surface-3 text-muted',
  brand: 'border-accent-line bg-accent-soft text-accent',
  success: 'border-ok-line bg-ok-soft text-ok',
  warning: 'border-warn-line bg-warn-soft text-warn',
  danger: 'border-bad-line bg-bad-soft text-bad',
};

export function Badge({ children, variant = 'neutral', className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
