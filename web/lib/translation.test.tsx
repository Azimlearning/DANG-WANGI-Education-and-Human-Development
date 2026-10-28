import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { EnvironmentBlock } from "@synapse/schema";
import { LangProvider } from "./i18n";
import { clearTranslationCache, fetchTranslation, LabLanguageNote, useTranslatedBlock } from "./translation";

afterEach(() => {
  cleanup();
  localStorage.clear();
  clearTranslationCache();
});

const block = (id: string): EnvironmentBlock =>
  ({ type: "Environment", id, title: id, meta: { status: "ready", error: null }, lane: "instantiate", label: "kit-verified", kitVersion: "0.1.0", htmlSha256: "0".repeat(64), html: "<p>x</p>", citations: [], checked: { layers: [], controlsExercised: 0, gridPoints: 0, referenceCases: 0, readouts: 0, models: [], limits: "" }, planSummary: "" }) as EnvironmentBlock;

function fakeFetch(routes: Record<string, unknown | null>): typeof fetch {
  return (async (url: string) => {
    const path = new URL(url).pathname;
    const body = routes[path];
    return { ok: body !== null && body !== undefined, json: async () => body } as Response;
  }) as unknown as typeof fetch;
}

describe("fetchTranslation", () => {
  it("is null when the server lists no Malay translation", async () => {
    const f = fakeFetch({ "/library/a/translations": { translations: [] } });
    expect(await fetchTranslation("a", "http://x", f)).toBeNull();
  });

  it("fetches the translated Environment through the library route and says whether it is a draft", async () => {
    const f = fakeFetch({
      "/library/a/translations": { translations: [{ lang: "ms", envId: "a_ms-1", status: "draft", reviewer: null, reviewedOn: null }] },
      "/library/a_ms-1": block("a_ms-1"),
    });
    const found = await fetchTranslation("a", "http://x", f);
    expect(found?.block.id).toBe("a_ms-1");
    expect(found?.draft).toBe(true);
  });

  it("is null when the translated Environment is refused by the gate", async () => {
    const f = fakeFetch({
      "/library/a/translations": { translations: [{ lang: "ms", envId: "a_ms-1", status: "reviewed", reviewer: "R", reviewedOn: "2026-11-01" }] },
      "/library/a_ms-1": null,
    });
    expect(await fetchTranslation("a", "http://x", f)).toBeNull();
  });

  it("does not remember a network failure", async () => {
    const bad = (async () => {
      throw new Error("offline");
    }) as unknown as typeof fetch;
    await expect(fetchTranslation("n", "http://x", bad)).rejects.toThrow();
    const good = fakeFetch({ "/library/n/translations": { translations: [] } });
    expect(await fetchTranslation("n", "http://x", good)).toBeNull();
  });
});

function Shown({ original }: { original: EnvironmentBlock }) {
  const { block: shown, state, draft } = useTranslatedBlock(original);
  return (
    <div>
      <p data-testid="id">{shown.id}</p>
      <LabLanguageNote state={state} draft={draft} />
    </div>
  );
}

describe("useTranslatedBlock", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("is the original, with no note, while English is chosen", () => {
    render(
      <LangProvider>
        <Shown original={block("a")} />
      </LangProvider>,
    );
    expect(screen.getByTestId("id").textContent).toBe("a");
    expect(screen.queryByTestId("lab-language-note")).toBeNull();
  });

  it("says a lab is not available in Malay when the server has no translation", async () => {
    localStorage.setItem("synapse-lang", "ms");
    vi.stubGlobal("fetch", fakeFetch({ "/library/solo/translations": { translations: [] } }));
    render(
      <LangProvider>
        <Shown original={block("solo")} />
      </LangProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("lab-language-note").textContent).toMatch(/belum tersedia dalam Bahasa Melayu/)); // the page strings are Malay drafts, shown by default (D-68)
    expect(screen.getByTestId("id").textContent).toBe("solo");
    vi.unstubAllGlobals();
  });

  it("shows the translated block when there is one", async () => {
    localStorage.setItem("synapse-lang", "ms");
    vi.stubGlobal(
      "fetch",
      fakeFetch({
        "/library/pair/translations": { translations: [{ lang: "ms", envId: "pair_ms-9", status: "reviewed", reviewer: "R", reviewedOn: "2026-11-01" }] },
        "/library/pair_ms-9": block("pair_ms-9"),
      }),
    );
    render(
      <LangProvider>
        <Shown original={block("pair")} />
      </LangProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("id").textContent).toBe("pair_ms-9"));
    expect(screen.queryByTestId("lab-language-note")).toBeNull(); // reviewed: no draft mark
    vi.unstubAllGlobals();
  });
});
