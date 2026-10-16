import { describe, expect, it } from "vitest";
import { AskError, parseEnvironmentBlock, parseStreamEvent, readSse, streamAsk } from "./stream";

const block = (over: Record<string, unknown> = {}) => ({
  type: "Environment",
  id: "reference-spring-abc",
  meta: { status: "ready", error: null },
  title: "A spring",
  lane: "instantiate",
  label: "dev-fixture",
  kitVersion: "0.0.1",
  htmlSha256: "0".repeat(64),
  html: "<p>x</p>",
  citations: [{ source: "UNVERIFIED", page: null, quote: null, verified: false }],
  planSummary: "A fixture.",
  ...over,
});

const bytes = (s: string) => new TextEncoder().encode(s);
function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(c) {
      for (const chunk of chunks) c.enqueue(bytes(chunk));
      c.close();
    },
  });
}
async function collect(it: AsyncGenerator<string>) {
  const out: string[] = [];
  for await (const x of it) out.push(x);
  return out;
}

describe("parseStreamEvent", () => {
  it("accepts every event the server sends", () => {
    expect(parseStreamEvent({ type: "meta", requestId: "r", lane: "instantiate", label: "dev-fixture", kitVersion: "0.0.1" })).toMatchObject({ type: "meta" });
    expect(parseStreamEvent({ type: "text_delta", text: "hi" })).toEqual({ type: "text_delta", text: "hi" });
    expect(parseStreamEvent({ type: "environment", block: block() })).toMatchObject({ type: "environment" });
    expect(parseStreamEvent({ type: "error", error: { code: "not_found", message: "m", issues: [{ path: "a", message: "b" }], retryable: false } })).toMatchObject({ type: "error" });
    expect(parseStreamEvent({ type: "done" })).toEqual({ type: "done" });
  });
  it("ignores an unknown event type instead of crashing", () => {
    expect(parseStreamEvent({ type: "telepathy", x: 1 })).toBeNull();
    expect(parseStreamEvent("done")).toBeNull();
    expect(parseStreamEvent(null)).toBeNull();
    expect(parseStreamEvent([])).toBeNull();
  });
  it("ignores an unknown BLOCK type, and a malformed Environment, instead of crashing", () => {
    expect(parseStreamEvent({ type: "environment", block: { type: "QuizCard", id: "q" } })).toBeNull();
    expect(parseEnvironmentBlock(block({ type: "VerifiedLab" }))).toBeNull();
    expect(parseEnvironmentBlock(block({ lane: "improvise" }))).toBeNull();
    expect(parseEnvironmentBlock(block({ label: "trust-me" }))).toBeNull();
    expect(parseEnvironmentBlock(block({ html: 5 }))).toBeNull();
    expect(parseEnvironmentBlock(block({ citations: [{ source: "s", page: 1.5, quote: null, verified: false }] }))).toBeNull();
    expect(parseEnvironmentBlock(block({ meta: { status: "ready", error: { code: "x" } } }))).toBeNull();
  });
});

describe("readSse", () => {
  const wire = 'data: {"a":1}\n\ndata: {"b":2}\n\n';
  it("yields the data payloads", async () => {
    expect(await collect(readSse(streamOf([wire])))).toEqual(['{"a":1}', '{"b":2}']);
  });
  it("is correct however the bytes are chunked", async () => {
    for (const size of [1, 2, 3, 5, 7]) {
      const chunks = wire.match(new RegExp(`.{1,${size}}`, "gs")) ?? [];
      expect(await collect(readSse(streamOf(chunks)))).toEqual(['{"a":1}', '{"b":2}']);
    }
  });
  it("handles CRLF, comments, other fields and multi-line data", async () => {
    const crlf = ': keep-alive\r\n\r\nevent: x\r\ndata: one\r\ndata: two\r\n\r\n';
    expect(await collect(readSse(streamOf([crlf])))).toEqual(["one\ntwo"]);
  });
  it("does not split a multi-byte character across chunks", async () => {
    const all = bytes('data: "é≈"\n\n');
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        for (let i = 0; i < all.length; i++) c.enqueue(all.slice(i, i + 1));
        c.close();
      },
    });
    expect(await collect(readSse(body))).toEqual(['"é≈"']);
  });
  it("yields a final message that has no trailing blank line", async () => {
    expect(await collect(readSse(streamOf(["data: last"])))).toEqual(["last"]);
  });
});

describe("streamAsk", () => {
  const sse = (events: unknown[]) => events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
  const fakeFetch = (body: string, status = 200) =>
    (async () => new Response(body, { status, headers: { "content-type": status === 200 ? "text/event-stream" : "application/json" } })) as typeof fetch;

  it("yields validated events in order and skips what it does not understand", async () => {
    const body = sse([
      { type: "meta", requestId: "r", lane: "instantiate", label: "dev-fixture", kitVersion: "0.0.1" },
      { type: "text_delta", text: "a" },
      { type: "from_the_future" },
      { type: "environment", block: { type: "SomethingNew" } },
      { type: "environment", block: block() },
      { type: "done" },
    ]) + "data: not json\n\n";
    const seen: string[] = [];
    for await (const e of streamAsk("q", { baseUrl: "http://x/", fetchImpl: fakeFetch(body) })) seen.push(e.type);
    expect(seen).toEqual(["meta", "text_delta", "environment", "done"]);
  });
  it("turns a non-200 answer into an AskError carrying the envelope", async () => {
    const envelope = { code: "bad_request", message: "The question is empty.", issues: [], retryable: false };
    const run = async () => {
      for await (const _ of streamAsk("q", { baseUrl: "http://x", fetchImpl: fakeFetch(JSON.stringify(envelope), 400) })) void _;
    };
    await expect(run()).rejects.toBeInstanceOf(AskError);
    await expect(run()).rejects.toMatchObject({ message: "The question is empty.", envelope: { code: "bad_request" } });
  });
});
