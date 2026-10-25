// `guard()`: what a composite widget remembers about its own parts, so its audit can say whether a page changed them. A part is an element the Kit made; the guard keeps the
// attributes it was given (the ones that follow a number are given as a function) and the elements inside the widget. A page that adds an attribute (`fill-opacity`, `visibility`,
// `class`, `hidden`), changes one the Kit did not mean to change, or adds an element inside the widget (an opaque shape over the picture) is reported. All reads go through the
// primitives captured when the bundle loaded.

import { all, attrsOf, parentOf, textNodes, textOf } from "./dom";

type Attrs = Record<string, string>;

function same(a: Attrs, b: Attrs): boolean {
  const ka = Object.keys(a).sort();
  const kb = Object.keys(b).sort();
  return ka.length === kb.length && ka.every((k, i) => k === kb[i] && a[k] === b[k]);
}

export interface Guard {
  /** Register a part. `dynamic` gives the attributes that follow a number, as the Kit would set them now. */
  part(el: Element, dynamic?: () => Attrs): void;
  /** Register a widget's root: the elements inside it, now, are the only ones it may ever hold. */
  tree(root: Element): void;
  /** What a page changed, in words. Empty when nothing was. */
  problems(): string[];
}

export function guard(): Guard {
  const parts: { el: Element; base: Attrs; dynamic?: () => Attrs }[] = [];
  const trees: { root: Element; inside: Element[]; holders: Set<Element | null> }[] = [];
  return {
    part(el, dynamic) {
      const base = attrsOf(el);
      for (const k of Object.keys(dynamic ? dynamic() : {})) delete base[k];
      parts.push({ el, base, dynamic });
    },
    tree(root) {
      // The elements that hold text now are the only ones that may: text a page adds to anywhere else in the picture is a sentence the Kit did not write.
      const holders = new Set(textNodes(root).filter((n) => textOf(n).trim() !== "").map((n) => parentOf(n)));
      trees.push({ root, inside: all(root, "*"), holders });
    },
    problems() {
      const out: string[] = [];
      for (const p of parts) {
        if (!same(attrsOf(p.el), { ...p.base, ...(p.dynamic ? p.dynamic() : {}) })) {
          out.push("a part of a picture the Kit drew was changed by the page");
          break;
        }
      }
      for (const t of trees) {
        const now = all(t.root, "*");
        if (now.length !== t.inside.length || now.some((el, i) => el !== t.inside[i])) {
          out.push("an element was added to, or taken out of, a picture the Kit drew");
          break;
        }
        if (textNodes(t.root).some((n) => textOf(n).trim() !== "" && !t.holders.has(parentOf(n)))) {
          out.push("text was added to a picture the Kit drew");
          break;
        }
      }
      return out;
    },
  };
}
