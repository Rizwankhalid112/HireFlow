import { useEffect, useState } from 'react';

/*
 * Subscribes to a CSS media query from JS.
 *
 * Needed wherever a breakpoint must gate *behaviour* and not just styling:
 * Tailwind's `hidden xl:flex` still mounts the component, and a preview pane
 * that mounts on a phone would fire a server-side PDF render nobody ever sees.
 */
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    // Guarded for SSR and for jsdom, neither of which has matchMedia.
    () => (typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(query).matches
      : false),
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return undefined;
    }

    const list = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);

    setMatches(list.matches);
    list.addEventListener('change', onChange);
    return () => list.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}
