import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import raw from "./strings.json";
import { fallbackCount, LangDraftChip, LangNotice, LangProvider, LangSwitch, translate, type StringKey, useT } from "./i18n";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.unstubAllEnvs();
  vi.resetModules();
});

const KEYS = Object.keys(raw).filter((k) => k !== "_about") as StringKey[];
const entry = (k: StringKey) => (raw as unknown as Record<StringKey, { en: string; ms: string; reviewed: boolean }>)[k];
const places = (text: string) => (text.match(/\{\w+\}/g) ?? []).sort();
const digits = (text: string) => (text.match(/\d+/g) ?? []).sort();

describe("the string table", () => {
  it("every string has an English and a Malay, with the same places to fill and the same digits", () => {
    for (const k of KEYS) {
      const e = entry(k);
      expect(e.en, k).not.toBe("");
      expect(e.ms, k).not.toBe("");
      expect(places(e.ms), k).toEqual(places(e.en));
      expect(digits(e.ms), k).toEqual(digits(e.en));
    }
  });

  it("the Malay is not the English, apart from names that are the same in both", () => {
    const same = KEYS.filter((k) => entry(k).en === entry(k).ms);
    expect(same).toEqual([]);
  });

  it("no Malay string is reviewed until a person reviews it (the build assistant never flips the flag)", () => {
    expect(KEYS.filter((k) => entry(k).reviewed)).toEqual([]);
  });

  it("Malay is shown only for a reviewed string or when drafts are on; the rest is English", () => {
    expect(translate("ms", "present", undefined, false)).toBe("Present");
    expect(translate("ms", "present", undefined, true)).toBe("Paparkan");
    expect(translate("en", "present", undefined, true)).toBe("Present");
    expect(fallbackCount(false)).toBe(KEYS.length);
    expect(fallbackCount(true)).toBe(0);
  });

  it("fills the places in a string", () => {
    expect(translate("ms", "marksOf", { score: 2, marks: 3 }, true)).toBe("2 daripada 3 markah");
    expect(translate("en", "marksOf", { score: 2, marks: 3 })).toBe("2 of 3 marks");
  });
});

function Probe() {
  const t = useT();
  return <p>{t("present")}</p>;
}

describe("the switch", () => {
  beforeEach(() => localStorage.clear());

  it("starts in English; BM shows the Malay drafts with a draft mark by default, and remembers the choice", () => {
    render(
      <LangProvider>
        <LangSwitch />
        <LangNotice />
        <LangDraftChip />
        <Probe />
      </LangProvider>,
    );
    expect(screen.getByText("Present")).toBeTruthy();
    expect(screen.queryByTestId("lang-draft")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "BM" }));
    expect(screen.getByRole("button", { name: "BM" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Paparkan")).toBeTruthy(); // drafts are on by default (D-68)
    expect(screen.getByTestId("lang-draft").getAttribute("aria-label")).toMatch(/Draf terjemahan/); // and always marked
    expect(screen.queryByTestId("lang-notice")).toBeNull();
    expect(localStorage.getItem("synapse-lang")).toBe("ms");
    expect(document.documentElement.lang).toBe("ms");
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.queryByTestId("lang-draft")).toBeNull();
    expect(document.documentElement.lang).toBe("en");
  });

  it("with drafts turned off by the build, Malay falls back to English with a note", async () => {
    vi.stubEnv("NEXT_PUBLIC_BM_DRAFTS", "0");
    vi.resetModules();
    const mod = await import("./i18n");
    localStorage.setItem("synapse-lang", "ms");
    function Shown() {
      const t = mod.useT();
      return <p>{t("present")}</p>;
    }
    render(
      <mod.LangProvider>
        <mod.LangNotice />
        <mod.LangDraftChip />
        <Shown />
      </mod.LangProvider>,
    );
    expect(await screen.findByText("Present")).toBeTruthy();
    expect((await screen.findByTestId("lang-notice")).textContent).toMatch(/waiting for a reviewer/);
    expect(screen.queryByTestId("lang-draft")).toBeNull();
  });

  it("every control of the switch is at least 44 px tall by class", () => {
    render(
      <LangProvider>
        <LangSwitch compact />
      </LangProvider>,
    );
    for (const b of screen.getAllByRole("button")) expect(b.className).toMatch(/min-h-11|btn/);
  });
});
