import { describe, expect, it } from "vitest";
import { citationText, documentTitle } from "./citation";

describe("documentTitle", () => {
  it.each([
    ["textbook-physics-physics-f5-removed", "KSSM Physics Form 5 textbook"],
    ["textbook-physics-physics-f4-removed", "KSSM Physics Form 4 textbook"],
    ["textbook-chemistry-chemistry-f4", "KSSM Chemistry Form 4 textbook"],
    ["textbook-chemistry-chemistry-f5", "KSSM Chemistry Form 5 textbook"],
    ["textbook-biology-form-4-dlp-biology-f4", "KSSM Biology Form 4 textbook"],
    ["textbook-biology-form-5-dlp-biology-form-5", "KSSM Biology Form 5 textbook"],
  ])("%s", (id, title) => expect(documentTitle(id)).toBe(title));

  it("shows an id it does not recognise exactly as it is", () => {
    expect(documentTitle("UNVERIFIED (corpus not loaded until P2)")).toBe("UNVERIFIED (corpus not loaded until P2)");
    expect(documentTitle("notes-physics-f5")).toBe("notes-physics-f5");
  });
});

describe("citationText", () => {
  it("names the book and the PDF page", () => {
    expect(citationText({ source: "textbook-physics-physics-f5-removed", page: 36, verified: true })).toBe(
      "KSSM Physics Form 5 textbook, PDF page 36",
    );
  });
  it("says when a citation is not verified, and omits a missing page", () => {
    expect(citationText({ source: "UNVERIFIED (no textbook page has been checked for this Environment)", page: null, verified: false })).toBe(
      "UNVERIFIED (no textbook page has been checked for this Environment) (not verified)",
    );
  });
});
