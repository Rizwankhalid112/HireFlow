export function Card({ children, className = '', padded = true }) {
  return (
    <div
      className={`rounded-card border border-line bg-surface shadow-card ${padded ? 'p-4' : ''} ${className}`}
    >
      {children}
    </div>
  );
}

/* A card with a titled header rule. Most screens want this rather than a bare
   surface — it is what gives a dense page its horizontal rhythm. */
export function Panel({ title, description, action, children, className = '', bodyClass = 'p-4' }) {
  return (
    <div className={`rounded-card border border-line bg-surface shadow-card ${className}`}>
      {(title || action) && (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-[15px] font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </div>
  );
}
