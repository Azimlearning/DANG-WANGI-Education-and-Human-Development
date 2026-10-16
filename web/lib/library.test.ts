import { describe, expect, it } from "vitest";
import { sha256Hex } from "./hash";
import { ENV_ID, fetchEnvironment, shareUrl } from "./library";
import { AskError } from "./stream";

async function goodBlock() {
  const html = "<!doctype html><html><body>x</body></html>";
  return {
    type: "Environment",
    id: "spring-0123456789ab",
    meta: { status: "ready", error: null },
    title: "A spring",
    lane: "compose",
    label: "model-checked",
    kitVersion: "0.1.0",
    htmlSha256: await sha256Hex(html),
    html,
    citations: [{ source: "UNVERIFIED", page: null, quote: null, verified: false }],
    checked: { layers: ["scan"], controlsExercised: 1, gridPoints: 1, referenceCases: 1, readouts: 1, models: [], limits: "Checked by code." },
    planSummary: "p",
  };
}

const respond = (status: number, body: unknown): typeof fetch => (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

describe("share links", () => {
  it("builds a link from the origin and a safely encoded id", () => {
    expect(shareUrl("https://example.test/", "spring-0123456789ab")).toBe("https://example.test/e/spring-0123456789ab");
  });

  it("accepts only ids of the shape the server makes", () => {
    expect(ENV_ID.test("spring-0123456789ab")).toBe(true);
    for (const bad of ["", "../etc", "a/b", "A", "x".repeat(81), "a b", "a?b=1"]) expect(ENV_ID.test(bad)).toBe(false);
  });

  it("fetches a block through the library endpoint and validates it", async () => {
    let url = "";
    const block = await fetchEnvironment("spring-0123456789ab", {
      baseUrl: "http://api.test/",
      fetchImpl: (async (u: string) => {
        url = u;
        return new Response(JSON.stringify(await goodBlock()), { status: 200 });
      }) as unknown as typeof fetch,
    });
    expect(url).toBe("http://api.test/library/spring-0123456789ab");
    expect(block.title).toBe("A spring");
  });

  it("never requests a malformed id", async () => {
    let called = false;
    const fetchImpl = (async () => {
      called = true;
      return new Response("{}");
    }) as unknown as typeof fetch;
    await expect(fetchEnvironment("../secret", { baseUrl: "http://api.test", fetchImpl })).rejects.toBeInstanceOf(AskError);
    expect(called).toBe(false);
  });

  it("turns a refusal into the server's own message and rejects things that are not Environments", async () => {
    const envelope = { code: "verification_refused", message: "This Environment is not available.", issues: [], retryable: false };
    await expect(fetchEnvironment("spring-0123456789ab", { baseUrl: "http://api.test", fetchImpl: respond(422, envelope) })).rejects.toThrow("not available");
    await expect(fetchEnvironment("spring-0123456789ab", { baseUrl: "http://api.test", fetchImpl: respond(200, { type: "Other" }) })).rejects.toThrow("not an Environment");
    await expect(fetchEnvironment("spring-0123456789ab", { baseUrl: "http://api.test", fetchImpl: respond(500, "oops") })).rejects.toThrow("500");
  });
});
