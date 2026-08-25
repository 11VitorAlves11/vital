import { useEffect, useState } from "react";

/** Breakpoint at which navigation moves from bottom bar to sidebar (md, 768px). */
export const DESKTOP_QUERY = "(min-width: 768px)";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches,
  );

  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);

  return matches;
}

export function useIsDesktop(): boolean {
  return useMediaQuery(DESKTOP_QUERY);
}
