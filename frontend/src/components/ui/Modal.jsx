import { useEffect } from 'react';

export function Modal({ open, onClose, title, description, children, footer, size = 'md' }) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose?.();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  /* `full` is the mobile sheet: edge to edge, full height, and the body is left
     to the caller so it can own its own scrolling region. */
  const sizes = {
    sm: 'max-w-sm max-h-[85vh] overflow-y-auto rounded-2xl p-6',
    md: 'max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl p-6',
    lg: 'max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl p-6',
    full: 'max-w-none h-[100dvh] flex flex-col p-0',
  };
  const hasHeading = Boolean(title || description);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center ${
        size === 'full' ? '' : 'p-4'
      }`}
    >
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-slate-900/50 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        className={`relative w-full ${sizes[size]} border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900`}
      >
        {title ? (
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
        ) : null}
        {description ? (
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
        ) : null}
        {/* No heading means no gap to close — the caller is rendering its own. */}
        {children ? (
          <div className={`min-h-0 flex-1 ${hasHeading ? 'mt-4' : ''}`}>{children}</div>
        ) : null}
        {footer ? <div className="mt-6 flex justify-end gap-3">{footer}</div> : null}
      </div>
    </div>
  );
}
