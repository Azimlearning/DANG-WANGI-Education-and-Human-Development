import { describe, expect, it } from "vitest";
import { MAX_ITEMS, STORAGE_KEY, decode, empty, encode, list, load, mastery, record, save, validate } from "./progress";

const env = { id: "spring-0123456789ab", title: "Hooke's law" };
const at = (n: number) => new Date(Date.UTC(2026, 9, 16, 0, 0, n));

describe("progress", () => {
  it("counts tries and correct answers per Environment and never mutates the old state", () => {
    const a = record(empty(), env, "incorrect", at(1));
    const b = record(a, env, "correct", at(2));
    expect(a.items[env.id]).toMatchObject({ tries: 1, correct: 0 });
    expect(b.items[env.id]).toMatchObject({ tries: 2, correct: 1, title: "Hooke's law" });
  });

  it("describes mastery in words and does not call two answers secure", () => {
    const e = (tries: number, correct: number) => ({ id: "x", title: "t", tries, correct, last: at(0).toISOString() });
    expect(mastery(e(1, 1))).toBe("Just started");
    expect(mastery(e(2, 2))).toBe("Secure");
    expect(mastery(e(3, 1))).toBe("Getting there");
    expect(mastery(e(10, 7))).toBe("Secure");
    expect(mastery(e(10, 6))).toBe("Getting there");
  });

  it("lists the most recent first and forgets the oldest past the cap", () => {
    let s = empty();
    for (let i = 0; i < MAX_ITEMS + 5; i++) s = record(s, { id: `e${i}`, title: `T${i}` }, "correct", at(i));
    expect(Object.keys(s.items).length).toBe(MAX_ITEMS);
    expect(s.items["e0"]).toBeUndefined();
    expect(list(s)[0]!.id).toBe(`e${MAX_ITEMS + 4}`);
  });

  it("round-trips through an export code, including non-ASCII titles", () => {
    const s = record(empty(), { id: "a", title: "Daya: a spring, ½ extension" }, "correct", at(3));
    const code = encode(s);
    expect(code.startsWith("SYN1.")).toBe(true);
    expect(decode(code)).toEqual(s);
    expect(decode(`  ${code}\n`)).toEqual(s);
  });

  it("refuses a mistyped, truncated, forged or oversize code", () => {
    const code = encode(record(empty(), env, "correct", at(1)));
    const [head, body, sum] = code.split(".");
    expect(decode(`${head}.${body}.${sum!.replace(/./, "0")}`)).toBeNull();
    expect(decode(`${head}.${body!.slice(0, -4)}.${sum}`)).toBeNull();
    expect(decode("nonsense")).toBeNull();
    expect(decode("SYN1.@@@.00000000")).toBeNull();
    expect(decode(`SYN1.${"A".repeat(70000)}.00000000`)).toBeNull();
  });

  it("validates the shape: counts, correct no more than tries, bounded text, matching keys", () => {
    const good = { v: 1, items: { a: { id: "a", title: "t", tries: 2, correct: 1, last: at(1).toISOString() } } };
    expect(validate(good)).toEqual(good);
    const bad = (patch: object) => validate({ v: 1, items: { a: { ...good.items.a, ...patch } } });
    expect(bad({ correct: 3 })).toBeNull();
    expect(bad({ tries: -1 })).toBeNull();
    expect(bad({ tries: 1.5 })).toBeNull();
    expect(bad({ title: "x".repeat(500) })).toBeNull();
    expect(bad({ last: "yesterday" })).toBeNull();
    expect(bad({ id: "b" })).toBeNull();
    expect(validate({ v: 2, items: {} })).toBeNull();
    expect(validate({ v: 1, items: [] })).toBeNull();
  });

  it("survives storage that is missing, throws or holds rubbish", () => {
    expect(load(null)).toEqual(empty());
    expect(load({ getItem: () => { throw new Error("blocked"); } })).toEqual(empty());
    expect(load({ getItem: () => "{not json" })).toEqual(empty());
    expect(load({ getItem: (k: string) => (k === STORAGE_KEY ? JSON.stringify({ v: 1, items: { a: { id: "z" } } }) : null) })).toEqual(empty());
    expect(save(empty(), null)).toBe(false);
    expect(save(empty(), { setItem: () => { throw new Error("full"); } })).toBe(false);
    const box: Record<string, string> = {};
    const s = record(empty(), env, "correct", at(1));
    expect(save(s, { setItem: (k: string, v: string) => { box[k] = v; } })).toBe(true);
    expect(load({ getItem: (k: string) => box[k] ?? null })).toEqual(s);
  });
});
