// "Recently opened": the ids and titles of Environments this device has seen, kept in this browser only. V3 kept the whole HTML of a lab in localStorage and
// replayed it; V4 does not (D-38): an item here is only a pointer, and opening it fetches the Environment through the server's delivery gate again, so the page is
// re-checked and its hash re-verified every time. Nothing is sent anywhere.
import { ENV_ID } from "./library";

export interface RecentItem {
  id: string;
  title: string;
}

export const RECENT_KEY = "synapse-recent";
export const MAX_RECENT = 6;

export function loadRecent(): RecentItem[] {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]") as unknown;
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((x): x is RecentItem => typeof x === "object" && x !== null && typeof (x as RecentItem).id === "string" && typeof (x as RecentItem).title === "string" && ENV_ID.test((x as RecentItem).id))
      .map((x) => ({ id: x.id, title: x.title.slice(0, 80) }))
      .slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

function save(items: RecentItem[]): RecentItem[] {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(items));
  } catch {
    /* blocked storage: the list lasts for this visit only */
  }
  return items;
}

/** Newest first, no duplicates, at most `MAX_RECENT`. An id that is not a valid Environment id is ignored. */
export function addRecent(item: RecentItem): RecentItem[] {
  if (!ENV_ID.test(item.id)) return loadRecent();
  return save([{ id: item.id, title: item.title.slice(0, 80) }, ...loadRecent().filter((x) => x.id !== item.id)].slice(0, MAX_RECENT));
}

export function removeRecent(id: string): RecentItem[] {
  return save(loadRecent().filter((x) => x.id !== id));
}
