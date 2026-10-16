// The browser re-hashes the Environment's HTML before rendering (hard constraint 1). Pattern from Azimlearning/Arcana-v2,
// web/lib/labFrame.ts @ 21c6dcf5 (sha256Hex with SubtleCrypto), rewritten for Environment blocks.
import type { EnvironmentBlock } from "@synapse/schema";

/** The lower-case hex SHA-256 of `text` as UTF-8. */
export async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export type HashCheck = { ok: true } | { ok: false; reason: string };

/** Compare the block's HTML to the hash the server verified. Any failure, including no SubtleCrypto, is a refusal. */
export async function checkBlockHash(block: Pick<EnvironmentBlock, "html" | "htmlSha256">): Promise<HashCheck> {
  let actual: string;
  try {
    actual = await sha256Hex(block.html);
  } catch {
    return { ok: false, reason: "This browser cannot check the Environment's hash, so it is not shown." };
  }
  if (actual !== block.htmlSha256.toLowerCase()) {
    return { ok: false, reason: "The Environment's code does not match the hash the server verified, so it is not shown." };
  }
  return { ok: true };
}
