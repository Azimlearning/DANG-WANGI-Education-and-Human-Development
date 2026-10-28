"use client";

// English and Bahasa Melayu for the page's own words (W12, D-62). The words live in `strings.json`, one entry per string with its English, its Malay and whether a
// fluent reviewer has approved the Malay. Since D-68 the drafts are shown, always with a draft mark, unless the build turns them off (NEXT_PUBLIC_BM_DRAFTS=0); then a
// string nobody reviewed is shown in English, with a note saying so. Nothing here translates at run time and nothing is sent anywhere.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import raw from "./strings.json";

export type Lang = "en" | "ms";
type Entry = { en: string; ms: string; reviewed: boolean };
export type StringKey = Exclude<keyof typeof raw, "_about">;
const STRINGS = raw as unknown as Record<StringKey, Entry>;

/** Malay drafts are shown, marked, unless the build turns them off (NEXT_PUBLIC_BM_DRAFTS=0). On by default since D-68: no reviewer will be found. */
export const SHOW_DRAFTS = process.env.NEXT_PUBLIC_BM_DRAFTS !== "0";
const STORAGE_KEY = "synapse-lang";
const keys = Object.keys(STRINGS).filter((k) => k !== "_about") as StringKey[];

/** Whether the Malay of this string may be shown. */
export function malayAllowed(entry: { reviewed: boolean }, showDrafts: boolean = SHOW_DRAFTS): boolean {
  return entry.reviewed || showDrafts;
}

export type Vars = Record<string, string | number>;

/** The string for `key` in `lang`, with `{name}` places filled. Pure, so a test or a server can use it. */
export function translate(lang: Lang, key: StringKey, vars?: Vars, showDrafts: boolean = SHOW_DRAFTS): string {
  const entry = STRINGS[key];
  const text = lang === "ms" && malayAllowed(entry, showDrafts) ? entry.ms : entry.en;
  return vars ? text.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? "")) : text;
}

/** How many strings would be shown in English although Malay was asked for. */
export function fallbackCount(showDrafts: boolean = SHOW_DRAFTS): number {
  return keys.filter((k) => !malayAllowed(STRINGS[k], showDrafts)).length;
}

/** How many Malay strings that are shown are still drafts. */
export function draftCount(showDrafts: boolean = SHOW_DRAFTS): number {
  return showDrafts ? keys.filter((k) => !STRINGS[k].reviewed).length : 0;
}

export type T = (key: StringKey, vars?: Vars) => string;

interface LangContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: T;
  /** Malay was asked for and some of the page is still in English. */
  partial: boolean;
  /** Malay was asked for and some of what is shown is a draft nobody has reviewed. */
  drafts: boolean;
}

export const english: T = (key, vars) => translate("en", key, vars);
const DEFAULT: LangContextValue = { lang: "en", setLang: () => {}, t: english, partial: false, drafts: false };
const LangContext = createContext<LangContextValue>(DEFAULT);

function readSaved(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === "ms" ? "ms" : "en";
  } catch {
    return "en";
  }
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => setLangState(readSaved()), []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage blocked: the choice lasts for this visit */
    }
  }, []);
  const value = useMemo<LangContextValue>(
    () => ({
      lang,
      setLang,
      t: (key, vars) => translate(lang, key, vars),
      partial: lang === "ms" && fallbackCount() > 0,
      drafts: lang === "ms" && draftCount() > 0,
    }),
    [lang, setLang],
  );
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangContextValue {
  return useContext(LangContext);
}

export function useT(): T {
  return useContext(LangContext).t;
}

/** The EN|BM switch. Two buttons in a group, each at least 44 px, the current one pressed. */
export function LangSwitch({ compact = false }: { compact?: boolean }) {
  const { lang, setLang, t } = useLang();
  const base = `btn px-3 text-sm ${compact ? "min-h-11" : ""}`;
  return (
    <span role="group" aria-label={t("languageAria")} className="inline-flex gap-1">
      {(["en", "ms"] as const).map((code) => (
        <button key={code} type="button" aria-pressed={lang === code} lang={code} onClick={() => setLang(code)} className={`${base} ${lang === code ? "btn-primary" : "btn-ghost"}`}>
          {code === "en" ? "EN" : "BM"}
        </button>
      ))}
    </span>
  );
}

/** One line under the top bar when Malay is chosen but some of the page is still English (nothing reviewed yet). Nothing otherwise. */
export function LangNotice() {
  const { lang, t, partial } = useLang();
  if (lang !== "ms" || !partial) return null;
  return (
    <p role="status" data-testid="lang-notice" className="border-b-2 border-line bg-band px-4 py-1.5 text-sm text-ink-dim sm:px-6">
      {t("bmPending")}
    </p>
  );
}

/** A small chip in the top bar while the Malay shown is a draft nobody has reviewed. The full sentence is its accessible name and its tooltip. */
export function LangDraftChip() {
  const { lang, t, drafts } = useLang();
  if (lang !== "ms" || !drafts) return null;
  return (
    <span role="status" data-testid="lang-draft" title={t("bmDraftMark")} aria-label={t("bmDraftMark")} className="study-badge study-badge-free whitespace-nowrap">
      {t("draftShort")}
    </span>
  );
}
