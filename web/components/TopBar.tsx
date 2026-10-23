"use client";

// Adapted from Synapse v3: frontend/components/TopBar.tsx (Genui monorepo, commit 835a2cefda28). Kept: Axi and the wordmark, the theme toggle with its circular
// reveal. Changed: the toggle is 44 px (hard constraint 10; V3's was 32), it tells every open Environment frame the theme through an event (an opaque-origin frame
// cannot read it), and the streak and gem counters are not carried over (D-38: invented numbers).
import { useEffect, useState } from "react";
import { Mascot } from "./Mascot";
import { applyTheme, currentTheme, type Theme } from "../lib/theme";

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setTheme(currentTheme());
    setMounted(true);
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    const doc = document as Document & { startViewTransition?: (cb: () => void) => { ready: Promise<void> } };
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!doc.startViewTransition || reduce) {
      applyTheme(next);
      return;
    }
    const transition = doc.startViewTransition(() => applyTheme(next));
    transition.ready
      .then(() => {
        document.documentElement.animate(
          { clipPath: ["circle(0% at 50% 0%)", "circle(160% at 50% 0%)"] },
          { duration: 820, easing: "cubic-bezier(0.65, 0, 0.35, 1)", pseudoElement: "::view-transition-new(root)" },
        );
      })
      .catch(() => {
        /* transition skipped (for example a hidden tab): the theme is already applied */
      });
  };

  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="grid h-11 w-11 place-items-center rounded-full border-2 border-line bg-card text-ink-dim shadow-[0_2px_0_var(--line-2)] hover:text-ink"
    >
      {mounted && dark ? (
        <svg width="19" height="19" viewBox="0 0 20 20" fill="none" aria-hidden>
          <circle cx="10" cy="10" r="4" stroke="currentColor" strokeWidth="1.6" />
          <path d="M10 1.5v2.5M10 16v2.5M18.5 10H16M4 10H1.5M15.5 4.5l-1.8 1.8M6.3 13.7l-1.8 1.8M15.5 15.5l-1.8-1.8M6.3 6.3L4.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      ) : (
        <svg width="19" height="19" viewBox="0 0 20 20" fill="none" aria-hidden>
          <path d="M16.5 11.5A6.5 6.5 0 0 1 8.5 3.5a6.5 6.5 0 1 0 8 8z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  );
}

export function TopBar() {
  return (
    <header className="sticky top-0 z-20 border-b-2 border-line bg-canvas">
      <div className="flex w-full items-center justify-between px-4 py-2 sm:px-6">
        <a href="/" className="flex min-h-11 items-center gap-1.5" aria-label="Synapse, home">
          <Mascot mood="happy" size={34} />
          <span className="font-display text-[22px] font-bold tracking-tight text-ink">Synapse</span>
        </a>
        <ThemeToggle />
      </div>
    </header>
  );
}
