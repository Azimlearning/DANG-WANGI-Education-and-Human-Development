import { beforeEach, describe, expect, it } from "vitest";
import { audit } from "./audit";
import { environment } from "./environment";
import { KIT_VERSION } from "./index";
import { resetForTests } from "./provenance";
import { STYLE } from "./style";

// kit-guardian, W3 review: the audit used to skip its CSS rules for ANY head stylesheet with the id `syn-style`, so a page could make its own and number a list by
// CSS counter with no text node. The exemption is now for the stylesheet `environment()` made, with exactly the Kit's text, and nothing else. `@counter-style` is
// named in the forbidden list as well.
beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  resetForTests();
});

const stylesheetFindings = () => audit(KIT_VERSION).forbidden.filter((f) => f.what.includes("stylesheet"));

describe("the Kit's stylesheet and the CSS rules", () => {
  it("is not reported while it is the Kit's own and unedited", () => {
    environment({ title: "t", note: "n" });
    expect(document.getElementById("syn-style")?.textContent).toBe(STYLE);
    expect(stylesheetFindings()).toEqual([]);
  });

  it("a stylesheet a page made with the id syn-style is checked like any other, and the Kit still adds its own", () => {
    const fake = document.createElement("style");
    fake.id = "syn-style";
    fake.textContent = "ol{counter-reset:list-item 8}";
    document.head.appendChild(fake);
    environment({ title: "t", note: "n" });
    expect(document.head.querySelectorAll("style")).toHaveLength(2);
    expect(stylesheetFindings()).toHaveLength(1);
  });

  it("the Kit's own stylesheet is checked as soon as a page edits it", () => {
    environment({ title: "t", note: "n" });
    expect(stylesheetFindings()).toEqual([]);
    const own = document.getElementById("syn-style") as HTMLStyleElement;
    own.textContent += "ol{counter-reset:list-item 8}";
    expect(stylesheetFindings()).not.toEqual([]);
  });

  it("a copy of the Kit's text in a stylesheet the Kit did not make does not earn the exemption", () => {
    const copy = document.createElement("style");
    copy.id = "syn-style";
    copy.textContent = STYLE;
    document.head.appendChild(copy);
    expect(stylesheetFindings()).toHaveLength(1);
  });

  it("names @counter-style, which can draw a number through a list marker", () => {
    environment({ title: "t", note: "n" });
    const style = document.createElement("style");
    style.textContent = '@counter-style fx{system:fixed;symbols:"9.81"} ol{list-style-type:fx}';
    document.head.appendChild(style);
    expect(stylesheetFindings()).toHaveLength(1);
  });

  it("refuses every stylesheet the Kit did not make, even an ordinary one: a Kit page carries no CSS but the Kit's", () => {
    environment({ title: "t", note: "n" });
    const style = document.createElement("style");
    style.textContent = "p{color:#333;margin:0}";
    document.head.appendChild(style);
    expect(stylesheetFindings().map((f) => f.what)).toEqual(["a stylesheet the Kit did not make"]);
  });
});
