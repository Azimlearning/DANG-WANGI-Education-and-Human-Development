"use client";

// The Bahasa Melayu version of a lab (W12, D-62). A translation is another verified Environment, linked to the English one by the server. This asks the server for
// the link and, when there is one, for that Environment through the same delivery gate as any other; the frame then re-hashes it before it renders, exactly like the
// English one. Nothing here translates text, and a lab with no translation (or a draft the server will not show) stays English with a note saying so.
import type { EnvironmentBlock, TranslationsResponse } from "@synapse/schema";
import { useEffect, useState } from "react";
import { useLang, useT } from "./i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Found {
  block: EnvironmentBlock;
  draft: boolean;
}

const cache = new Map<string, Promise<Found | null>>();

/** The Malay version of the lab `id`, or null when there is none to show. A network failure is not remembered, so the next try asks again. */
export function fetchTranslation(id: string, baseUrl: string = API_BASE, fetcher: typeof fetch = fetch): Promise<Found | null> {
  const key = `${baseUrl}|${id}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const base = baseUrl.replace(/\/$/, "");
  const run = (async (): Promise<Found | null> => {
    const list = await fetcher(`${base}/library/${encodeURIComponent(id)}/translations`);
    if (!list.ok) return null;
    const body = (await list.json()) as TranslationsResponse;
    const ms = body.translations.find((t) => t.lang === "ms");
    if (!ms) return null;
    const res = await fetcher(`${base}/library/${encodeURIComponent(ms.envId)}`);
    if (!res.ok) return null;
    return { block: (await res.json()) as EnvironmentBlock, draft: ms.status === "draft" };
  })();
  cache.set(key, run);
  run.catch(() => cache.delete(key));
  return run;
}

export function clearTranslationCache(): void {
  cache.clear();
}

export type LabLanguage = "english" | "loading" | "translated" | "unavailable";

/** The block to show for the chosen language, and where that stands. English is always the original, untouched. */
export function useTranslatedBlock(block: EnvironmentBlock): { block: EnvironmentBlock; state: LabLanguage; draft: boolean } {
  const { lang } = useLang();
  const [found, setFound] = useState<{ id: string; result: Found | null } | "loading" | null>(null);
  useEffect(() => {
    if (lang !== "ms") {
      setFound(null);
      return;
    }
    let live = true;
    setFound("loading");
    fetchTranslation(block.id).then(
      (result) => live && setFound({ id: block.id, result }),
      () => live && setFound({ id: block.id, result: null }),
    );
    return () => {
      live = false;
    };
  }, [lang, block.id]);
  if (lang !== "ms" || found === null) return { block, state: "english", draft: false };
  if (found === "loading" || found.id !== block.id) return { block, state: "loading", draft: false };
  if (found.result === null) return { block, state: "unavailable", draft: false };
  return { block: found.result.block, state: "translated", draft: found.result.draft };
}

/** A line under a lab's header that says what language it is in when that is not obvious: still loading, not available, or a draft. */
export function LabLanguageNote({ state, draft }: { state: LabLanguage; draft: boolean }) {
  const t = useT();
  const text = state === "loading" ? t("labLoadingTranslation") : state === "unavailable" ? t("labNoTranslation") : state === "translated" && draft ? t("bmDraftMark") : null;
  if (!text) return null;
  return (
    <p role="status" data-testid="lab-language-note" className="border-b-2 border-line bg-band px-3 py-1 text-sm text-ink-dim">
      {text}
    </p>
  );
}
