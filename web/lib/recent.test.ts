import { beforeEach, describe, expect, it } from "vitest";
import { addRecent, loadRecent, MAX_RECENT, RECENT_KEY, removeRecent } from "./recent";

beforeEach(() => localStorage.clear());

describe("recently opened", () => {
  it("keeps newest first without duplicates and at most six", () => {
    for (let i = 0; i < 9; i++) addRecent({ id: `env-${i}`, title: `Title ${i}` });
    addRecent({ id: "env-3", title: "Title 3 again" });
    const items = loadRecent();
    expect(items).toHaveLength(MAX_RECENT);
    expect(items[0]).toEqual({ id: "env-3", title: "Title 3 again" });
    expect(items.filter((x) => x.id === "env-3")).toHaveLength(1);
  });

  it("removes one item", () => {
    addRecent({ id: "a-1", title: "A" });
    addRecent({ id: "b-2", title: "B" });
    expect(removeRecent("a-1").map((x) => x.id)).toEqual(["b-2"]);
  });

  it("refuses an id that could not be an Environment id and drops bad stored data", () => {
    expect(addRecent({ id: "../etc/passwd", title: "x" })).toEqual([]);
    localStorage.setItem(RECENT_KEY, JSON.stringify([{ id: "ok-1", title: "Fine" }, { id: 5, title: "no" }, { id: "has space", title: "no" }, "junk"]));
    expect(loadRecent()).toEqual([{ id: "ok-1", title: "Fine" }]);
    localStorage.setItem(RECENT_KEY, "{not json");
    expect(loadRecent()).toEqual([]);
  });

  it("stores only a pointer: an id and a title, never a page", () => {
    addRecent({ id: "env-1", title: "T" });
    expect(Object.keys(JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]")[0]).sort()).toEqual(["id", "title"]);
  });
});
