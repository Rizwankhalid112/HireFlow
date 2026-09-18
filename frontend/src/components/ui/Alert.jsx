import { Icon } from './Icon';

const variants = {
  info: { box: 'border-accent-line bg-accent-soft text-accent', icon: 'info' },
  success: { box: 'border-ok-line bg-ok-soft text-ok', icon: 'check' },
  warning: { box: 'border-warn-line bg-warn-soft text-warn', icon: 'warning' },
  error: { box: 'border-bad-line bg-bad-soft text-bad', icon: 'warning' },
};

export function Alert({ children, variant = 'info', className = '' }) {
  const { box, icon } = variants[variant];

  return (
    <div className={`flex items-start gap-2.5 rounded-control border px-3 py-2.5 text-xs leading-5 ${box} ${className}`}>
      <Icon name={icon} size={14} className="mt-0.5" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
