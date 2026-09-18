/*
 * One stroke-based icon set, drawn on a 24px grid.
 *
 * The app used to type its icons as literal characters — ← ↑ ↓ ✓ — which
 * render differently in every font, cannot inherit a disabled colour, and are
 * read aloud by screen readers as punctuation. These are SVG, take `currentColor`,
 * and are hidden from the accessibility tree: the label lives on the control.
 */

const paths = {
  dashboard: 'M3.75 3.75h5.5v6.5h-5.5zM14.75 3.75h5.5v4h-5.5zM14.75 11.75h5.5v8.5h-5.5zM3.75 14.75h5.5v5.5h-5.5z',
  cv: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4',
  match: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8.8a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4zM12 2v2M12 20v2M2 12h2M20 12h2',
  jobs: 'M4.5 7h15a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-15a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M2.5 12.5h19',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.6-3.6',
  location: 'M20 10c0 5.5-8 12-8 12s-8-6.5-8-12a8 8 0 1 1 16 0ZM12 7.4a2.6 2.6 0 1 0 0 5.2 2.6 2.6 0 0 0 0-5.2z',
  check: 'm5 12.5 5 5 9-10',
  chevronDown: 'm8 10 4 4 4-4',
  chevronLeft: 'm14 6-6 6 6 6',
  chevronRight: 'm10 6 6 6-6 6',
  arrowUp: 'M12 19V5M6 11l6-6 6 6',
  arrowDown: 'M12 5v14M6 13l6 6 6-6',
  plus: 'M12 5v14M5 12h14',
  trash: 'M4 7h16M9.5 7V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5V7M6.5 7l.8 12a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.8-12',
  external: 'M14 4h6v6M20 4l-9 9M18 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5',
  sun: 'M12 3v2M12 19v2M5.6 5.6 7 7M17 17l1.4 1.4M3 12h2M19 12h2M5.6 18.4 7 17M17 7l1.4-1.4M12 8.4a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2z',
  moon: 'M20 14.2A8.2 8.2 0 0 1 9.8 4a8.2 8.2 0 1 0 10.2 10.2z',
  close: 'M6 6l12 12M18 6 6 18',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8h.01',
  warning: 'M12 4.5 2.8 20h18.4zM12 10v4M12 17h.01',
  download: 'M12 4v11M8 11.5l4 4 4-4M5 19h14',
  upload: 'M12 19V8M8 11.5 12 7.5l4 4M5 4h14',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5.5l3.5 2',
  menu: 'M4 6h16M4 12h16M4 18h16',
  sparkle: 'M12 3.5 13.7 9l5.5 1.7-5.5 1.7L12 18l-1.7-5.6L4.8 10.7 10.3 9z',
  logout: 'M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l4-4-4-4M14 12H3',
  copy: 'M8 8h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2zM16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2',
  refresh: 'M20 11a8 8 0 1 0-.6 4M20 5v6h-6',
  swap: 'M4 8h13l-3-3M20 16H7l3 3',
  /* The product mark: a rising line. Geometry matches public/favicon.svg. */
  mark: 'M4 18 9.5 12 14 15.5 20 7',
};

export function Icon({ name, size = 16, className = '', strokeWidth = 1.7 }) {
  const d = paths[name];
  if (!d) return null;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
    >
      <path d={d} />
    </svg>
  );
}

/* The product mark. Its geometry matches public/favicon.svg. */
export function Logo({ size = 24, className = '' }) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-[7px] bg-accent text-accent-on ${className}`}
      style={{ width: size, height: size }}
    >
      <Icon name="mark" size={size * 0.6} strokeWidth={2.6} />
    </span>
  );
}
