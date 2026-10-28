// The Environment block: the one thing that carries code across the wire. It is minted only by the verifier module and
// re-derived by the delivery gate from the stored record (CLAUDE.md hard constraint 1). The browser re-hashes `html`
// against `htmlSha256` before it renders anything.
//
// Adding a variant is a fixed sequence (preflight 5): add the interface, add it to the union, `pnpm codegen`,
// `pnpm codegen:check`, then give the web registry an entry and render states.

import type { ErrorEnvelope } from "./errors";

/** How the Environment was produced, decided by what verification it survives (hard constraint 3). */
export type Lane = "instantiate" | "compose" | "free";

/**
 * The trust label the student sees (D-21). `model-checked`: passed every deterministic layer, no verified textbook source.
 * `kit-verified`: also has a citation whose quote was verified against the corpus (P2). `reviewed` and `canonical` need a
 * human (hard constraints 3 and 4).
 */
export type TrustLabel = "kit-verified" | "model-checked" | "reviewed" | "canonical";

export type BlockStatus = "empty" | "loading" | "partial" | "ready" | "error";

export interface BlockMeta {
  status: BlockStatus;
  /** Why the block failed. Non-null if and only if status is "error". */
  error: ErrorEnvelope | null;
}

/** Where a claim in an Environment comes from. In P0 every citation is explicitly unverified (no corpus until P2). */
export interface Citation {
  source: string;
  /** @int */
  page: number | null;
  quote: string | null;
  verified: boolean;
  /** The number printed on the book's own page, when it is known (the PDF page is not what a student sees on paper). Display only: the proof is `quote` on `page`. @int */
  printedPage?: number | null;
}

/** A science micro-model an Environment uses, with the parameters it was built with. */
export interface ModelUse {
  id: string;
  params: Record<string, number>;
}

/** What was actually checked, recorded by the verifier and shown to the student (enhancement N10, hard constraint 11). */
export interface CheckedSummary {
  /** The layers that ran, for example postprocess, scan, render, provenance, grid, reference. */
  layers: string[];
  /** @int */
  controlsExercised: number;
  /** @int */
  gridPoints: number;
  /** @int */
  referenceCases: number;
  /** @int */
  readouts: number;
  models: ModelUse[];
  /** One plain sentence on what this does NOT show. */
  limits: string;
}

export interface EnvironmentBlock {
  type: "Environment";
  /** Non-empty. Stable across updates: a later block with the same id replaces this one. */
  id: string;
  meta: BlockMeta;
  title: string;
  lane: Lane;
  label: TrustLabel;
  /** Kit semver the HTML was composed over, for example "0.0.1". A behaviour change bumps it and marks stored copies stale. */
  kitVersion: string;
  /** Lower-case hex SHA-256 of `html` as UTF-8. */
  htmlSha256: string;
  html: string;
  citations: Citation[];
  checked: CheckedSummary;
  /** One plain sentence on what was composed and what was checked. */
  planSummary: string;
}

/** The languages an Environment can be read in. English is the original; Bahasa Melayu is a second Environment built from a translated Plan (D-62). */
export type Language = "en" | "ms";

/** A translation of an Environment: another verified Environment, linked to the original, with its review state. */
export interface Translation {
  lang: Language;
  /** The id of the translated Environment. Open it like any other: it goes through the same delivery gate. */
  envId: string;
  /** `draft`: written but not yet read by a fluent reviewer. `reviewed`: a person approved every string. */
  status: "draft" | "reviewed";
  reviewer: string | null;
  /** The date of the review, ISO 8601. */
  reviewedOn: string | null;
}

/** What `GET /library/{id}/translations` answers. A draft is listed only when the server is set to show drafts (a demo or a review session). */
export interface TranslationsResponse {
  translations: Translation[];
}

export type Block = EnvironmentBlock;
