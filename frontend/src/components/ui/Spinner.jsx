export function Spinner({ className = '', size = 20 }) {
  return (
    <div className={`flex items-center justify-center ${className}`} role="status" aria-label="Loading">
      <span
        className="animate-spin rounded-full border-2 border-line-strong border-t-accent"
        style={{ width: size, height: size }}
      />
    </div>
  );
}
