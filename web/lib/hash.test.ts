import { describe, expect, it } from "vitest";
import { checkBlockHash, sha256Hex } from "./hash";

describe("hash", () => {
  it("matches the SHA-256 test vector for 'abc'", async () => {
    expect(await sha256Hex("abc")).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
  it("hashes UTF-8, not UTF-16", async () => {
    // The UTF-8 bytes of "é" are c3 a9; their SHA-256 is computed independently by Node's crypto in the test.
    const { createHash } = await import("node:crypto");
    expect(await sha256Hex("é")).toBe(createHash("sha256").update(Buffer.from([0xc3, 0xa9])).digest("hex"));
    expect(await sha256Hex("é")).not.toBe(await sha256Hex("e"));
  });
  it("accepts matching html and refuses a one-character change", async () => {
    const html = "<!doctype html><p>hi</p>";
    const htmlSha256 = await sha256Hex(html);
    expect(await checkBlockHash({ html, htmlSha256 })).toEqual({ ok: true });
    const bad = await checkBlockHash({ html: html + " ", htmlSha256 });
    expect(bad.ok).toBe(false);
  });
});
