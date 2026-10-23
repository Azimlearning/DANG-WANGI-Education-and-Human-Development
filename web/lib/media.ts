"use client";

import { useEffect, useState } from "react";

/** True when the viewport matches `query`. False until mounted, so the server render and the first client render agree. Used to mount exactly ONE copy of an
 *  Environment frame (a hidden second copy would run a second sandbox and double every bridge event). */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);
  return matches;
}

/** The width at which the lab bench becomes its own column beside the conversation (Tailwind's `xl`). */
export const WIDE_QUERY = "(min-width: 1280px)";
