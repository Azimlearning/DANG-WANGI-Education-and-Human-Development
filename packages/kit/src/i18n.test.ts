import { beforeEach, describe, expect, it } from "vitest";
import { audit, violations } from "./audit";
import { conceptCheck } from "./concept_check";
import { environment } from "./environment";
import { experiment } from "./experiment";
import { hintLadder } from "./hints";
import { WORDS, kt, language, type WordKey } from "./i18n";
import { KIT_VERSION } from "./index";
import { predictCard } from "./predict_card";
import { resetForTests } from "./provenance";
import { readout } from "./readout";
import { reset } from "./reset";
import { hookes } from "./science/hookes";
import { slider } from "./slider";
import { springScene } from "./scene";
import { table } from "./table";
import { workedSolution } from "./worked_solution";

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

// Sample arguments for the entries that take them, so every word can be rendered in both languages.
const ARGS: Partial<Record<WordKey, unknown[]>> = {
  graphOf: ["Force", "Load", "A graph."],
  against: ["Force", "Load"],
  massCount: [3],
  massesToHang: ["Load"],
  hangerHolding: ["two masses"],
  massName: ["A", true],
  springHanging: ["stretched a little"],
  buretteScene: ["full", true],
  fermentActive: ["steady bubbling"],
  fermentScene: ["Nothing."],
  orbitScene: ["Outcome.", "Sketch."],
};

describe("the Kit's fixed words", () => {
  const SAME_IN_BOTH = new Set<string>(["planet7"]);
  it("every word has English and Bahasa Melayu, and the Malay is not the English", () => {
    for (const key of Object.keys(WORDS) as WordKey[]) {
      const args = ARGS[key] ?? [];
      environment({ title: "t", note: "n", lang: "en" });
      const en = kt(key, ...(args as never));
      environment({ title: "t", note: "n", lang: "ms" });
      const ms = kt(key, ...(args as never));
      expect(en, key).not.toBe("");
      expect(ms, key).not.toBe("");
      // A proper name that is the same word in both languages (the planet Uranus) is listed here by name, never waved through in general.
      if (!SAME_IN_BOTH.has(key)) expect(ms, `${key} is not translated`).not.toBe(en);
      document.body.innerHTML = "";
      resetForTests();
    }
  });

  it("the language is English unless the page says otherwise, and only two languages exist", () => {
    environment({ title: "t", note: "n" });
    expect(language()).toBe("en");
    document.body.innerHTML = "";
    resetForTests();
    environment({ title: "t", note: "n", lang: "ms" });
    expect(language()).toBe("ms");
    expect(() => environment({ title: "t", note: "n", lang: "fr" as never })).toThrow(RangeError);
  });

  it("the digits in a fixed word agree between the languages (a number must be backed in both)", () => {
    for (const key of Object.keys(WORDS) as WordKey[]) {
      const args = ARGS[key] ?? [];
      environment({ title: "t", note: "n", lang: "en" });
      const en = kt(key, ...(args as never)).match(/\d+/g) ?? [];
      environment({ title: "t", note: "n", lang: "ms" });
      const ms = kt(key, ...(args as never)).match(/\d+/g) ?? [];
      expect(ms, key).toEqual(en);
      document.body.innerHTML = "";
      resetForTests();
    }
  });
});

describe("a Malay page", () => {
  it("is built in Malay, answers to the same audit, and its chrome words are Malay", () => {
    const env = environment({ title: "Mengapa spring meregang?", note: "Gantung beban pada spring.", kicker: "Makmal fizik interaktif", tryThis: "Ubah beban.", lang: "ms" });
    const load = slider(env, { id: "load", label: "Beban", unit: "N", min: 0, max: 10, value: 2 });
    const extension = hookes({ k: 50, load });
    readout(env, { label: "Pemanjangan", unit: "m", value: extension, digits: 3 });
    springScene(env, { extension, full: 0.2 });
    table(env, { caption: "Keputusan", columns: [{ label: "Beban", unit: "N", value: load, digits: 1 }] });
    reset(env);
    predictCard(env, { prompt: "Apakah yang berlaku?", choices: ["Ia meregang", "Ia memendek"], reveal: "Lihat bacaan." });
    hintLadder(env, { hints: ["Fikirkan daya."] });
    conceptCheck(env, { question: "Soalan?", options: ["A", "B"], correct: 0, explanation: "Kerana daya." });
    workedSolution(env, { steps: ["Darabkan."] });
    experiment(env, { aim: "Mengkaji spring", hypothesis: "Lebih beban, lebih regangan", independent: "Beban", dependent: "Pemanjangan", controlled: ["Spring"], apparatus: ["Spring", "Pembaris"] });
    const text = document.body.textContent ?? "";
    expect(text).toContain("Cuba ini:");
    expect(text).toContain("Idea utama:");
    expect(text).toContain("Rekod");
    expect(text).toContain("Tunjukkan petunjuk");
    expect(text).toContain("Set semula");
    expect(text).not.toContain("Key idea:");
    expect(text).not.toContain("Show a hint");
    expect(document.querySelector(".syn-stage")?.getAttribute("aria-label")).toBe("Pentas");
    expect(violations(audit(KIT_VERSION))).toEqual([]);
  });

  it("an English page after a Malay one is English again", () => {
    environment({ title: "t", note: "n", lang: "ms" });
    document.body.innerHTML = "";
    resetForTests();
    const env = environment({ title: "t", note: "n" });
    reset(env);
    expect(document.body.textContent).toContain("Reset");
    expect(document.body.textContent).not.toContain("Set semula");
  });
});
