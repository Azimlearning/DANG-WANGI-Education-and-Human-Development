import { beforeEach, describe, expect, it, vi } from "vitest";
import { applyTheme, currentTheme, isTheme, THEME_EVENT, themeMessage } from "./theme";

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});

describe("theme", () => {
  it("accepts only light and dark", () => {
    expect(["light", "dark"].every(isTheme)).toBe(true);
    expect([undefined, null, "", "neon", 1].some(isTheme)).toBe(false);
  });

  it("applies, remembers and announces a choice", () => {
    const heard = vi.fn();
    window.addEventListener(THEME_EVENT, heard);
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("synapse-theme")).toBe("dark");
    expect(currentTheme()).toBe("dark");
    expect(heard).toHaveBeenCalledTimes(1);
    window.removeEventListener(THEME_EVENT, heard);
  });

  it("still applies the choice when storage is blocked", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    spy.mockRestore();
  });

  it("builds the one message the frame accepts", () => {
    expect(themeMessage("dark")).toEqual({ type: "synapse_theme", theme: "dark" });
  });
});
