// The theme choice lives on <html data-theme> (set before first paint by a script in the layout). Changing it also tells every open Environment frame, because
// a sandboxed opaque-origin frame cannot read the host's attribute: `EnvironmentFrame` listens for `THEME_EVENT` and posts the theme to its frame.
export type Theme = "light" | "dark";

export const THEME_EVENT = "synapse-theme";
const STORAGE_KEY = "synapse-theme";

export function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

/** The theme in force now: the attribute if set, else the system preference. */
export function currentTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const set = document.documentElement.dataset.theme;
  if (isTheme(set)) return set;
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Apply and remember a choice. A blocked storage only means the choice lasts for this visit. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* private mode or blocked storage: session only */
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}

/** The one message the host sends into a frame. The Kit accepts exactly this shape from its parent and nothing else. */
export function themeMessage(theme: Theme): { type: "synapse_theme"; theme: Theme } {
  return { type: "synapse_theme", theme };
}
