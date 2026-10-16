import type { EnvironmentBlock, ErrorEnvelope } from "@synapse/schema";
import { AskError, parseEnvironmentBlock, parseErrorEnvelope } from "./stream";

/** Ids are `<slug>-<12 hex>`; anything else is refused before it can reach a URL. */
export const ENV_ID = /^[a-z0-9][a-z0-9_-]{0,79}$/;

export function shareUrl(origin: string, id: string): string {
  return `${origin.replace(/\/$/, "")}/e/${encodeURIComponent(id)}`;
}

export interface LibraryOptions {
  baseUrl: string;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
}

/** One stored Environment through the server's delivery gate. The block is validated here and its hash is checked again by the frame before it renders. */
export async function fetchEnvironment(id: string, options: LibraryOptions): Promise<EnvironmentBlock> {
  if (!ENV_ID.test(id)) throw new AskError("That link is not a valid Environment link.", null);
  const doFetch = options.fetchImpl ?? fetch;
  const response = await doFetch(`${options.baseUrl.replace(/\/$/, "")}/library/${encodeURIComponent(id)}`, { signal: options.signal });
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    const envelope: ErrorEnvelope | null = parseErrorEnvelope(body);
    throw new AskError(envelope?.message ?? `The server answered ${response.status}.`, envelope);
  }
  const block = parseEnvironmentBlock(body);
  if (!block) throw new AskError("The server sent something that is not an Environment.", null);
  return block;
}
