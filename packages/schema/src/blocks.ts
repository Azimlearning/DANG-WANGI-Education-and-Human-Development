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
 * The trust label the student sees. `dev-fixture` is a P0-only label for hand-written fixtures and is removed in P1.
 * `kit-verified` needs a textbook citation; `canonical` needs human review (hard constraints 3 and 4).
 */
export type TrustLabel = "dev-fixture" | "kit-verified" | "model-checked" | "reviewed" | "canonical";

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
  /** One plain sentence on what was composed and what was checked. */
  planSummary: string;
}

export type Block = EnvironmentBlock;
