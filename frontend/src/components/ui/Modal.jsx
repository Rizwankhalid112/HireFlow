import { useEffect } from 'react';

import { IconButton } from './Button';

/* `full` is the mobile preview sheet: edge to edge, full height, and the body
   is left to the caller so it owns its own scrolling region. */
const sizes = {
  sm: 'max-w-sm max-h-[85vh] overflow-y-auto rounded-card',
  md: 'max-w-lg max-h-[85vh] overflow-y-auto rounded-card',
  lg: 'max-w-2xl max-h-[85vh] overflow-y-auto rounded-card',
  full: 'max-w-none h-[100dvh] flex flex-col',
};

export function Modal({ open, onClose, title, description, children, footer, size = 'md' }) {
  useEffect(() => {
    if (!open) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose?.();
    };

    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const isFull = size === 'full';
  const hasHeading = Boolean(title || description);

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${isFull ? '' : 'p-4'}`}>
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-ink/40 backdrop-blur-[2px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        className={`relative w-full border border-line bg-surface shadow-pop ${sizes[size]}`}
      >
        {hasHeading && (
          <div className={`flex items-start justify-between gap-4 ${isFull ? 'border-b border-line p-4' : 'px-5 pt-5'}`}>
            <div className="min-w-0">
              {title && <h2 className="text-[15px] font-semibold text-ink">{title}</h2>}
              {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
            </div>
            <IconButton icon="close" label="Close" onClick={onClose} size="sm" />
          </div>
        )}

        {children && (
          <div className={isFull ? 'min-h-0 flex-1' : `px-5 ${hasHeading ? 'pt-4' : 'pt-5'}`}>{children}</div>
        )}

        {footer && <div className="flex justify-end gap-2 px-5 pt-5 pb-5">{footer}</div>}
        {!footer && !isFull && <div className="pb-5" />}
      </div>
    </div>
  );
}
