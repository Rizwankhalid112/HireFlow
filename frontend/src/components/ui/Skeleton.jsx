/*
 * Loading placeholders shaped like the thing that is coming.
 *
 * Every loading state in the app used to be the same centred spinner, which
 * reads as a page reload even when the fetch takes 200ms. A block that already
 * occupies the right space reads as "nearly there" and stops the layout
 * jumping when the data lands.
 */

export function Skeleton({ className = '', w, h = 10 }) {
  return (
    <span
      aria-hidden="true"
      className={`block animate-pulse rounded bg-surface-3 ${className}`}
      style={{ width: w, height: h }}
    />
  );
}

export function SkeletonText({ lines = 3, className = '' }) {
  const widths = ['92%', '78%', '85%', '64%', '88%'];

  return (
    <div className={`flex flex-col gap-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} w={widths[i % widths.length]} h={9} />
      ))}
    </div>
  );
}

/* A list of card-shaped rows — the jobs list, any section list. */
export function SkeletonRows({ rows = 5, className = '' }) {
  return (
    <div className={`flex flex-col gap-2 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="rounded-card border border-line bg-surface p-3.5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <Skeleton w="45%" h={13} />
              <Skeleton w="62%" h={9} />
              <Skeleton w="38%" h={9} />
            </div>
            <Skeleton w={78} h={18} className="rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}
