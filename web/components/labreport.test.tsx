import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { applyLabPart, EMPTY_REPORT, hasReport, NO_WRITING, reportFileName, reportText, type LabReportData } from "../lib/labreport";
import { parseBridgeMessage } from "../lib/sandbox";
import { LabReport } from "./LabReport";

afterEach(cleanup);

const table = { part: "table" as const, caption: "Load and extension", columns: [{ label: "Load", unit: "N" }, { label: "Extension", unit: "m" }], rows: [["2.0", "0.040"], ["4.0", "0.080"]] };
const exp = { part: "experiment" as const, fields: [["Aim", "To find how the extension depends on the load."], ["Hypothesis", "It is proportional."]] as [string, string][] };
const steps = { part: "steps" as const, steps: ["Hang a load.", "Read the extension."] };

function full(): LabReportData {
  return [exp, steps, table].reduce(applyLabPart, EMPTY_REPORT);
}

describe("the bridge parser for lab parts", () => {
  it("accepts what the Kit sends", () => {
    for (const part of [exp, steps, table]) expect(parseBridgeMessage({ type: "synapse_lab", ...part })).toEqual({ type: "synapse_lab", ...part });
  });
  it.each([
    ["a row with the wrong number of cells", { ...table, rows: [["1"]] }],
    ["a cell that is not text", { ...table, rows: [["1", 2]] }],
    ["too many rows", { ...table, rows: Array.from({ length: 31 }, () => ["1", "2"]) }],
    ["an over-long step", { ...steps, steps: ["x".repeat(301)] }],
    ["too many steps", { ...steps, steps: Array.from({ length: 9 }, () => "x") }],
    ["a field that is not a pair", { ...exp, fields: [["Aim"]] }],
    ["an unknown part", { part: "script", html: "<b>" }],
    ["a table with no columns", { ...table, columns: [], rows: [] }],
  ])("refuses %s", (_name, part) => {
    expect(parseBridgeMessage({ type: "synapse_lab", ...part })).toBeNull();
  });
});

describe("the report model", () => {
  it("replaces a table with each snapshot instead of adding to it", () => {
    const once = applyLabPart(EMPTY_REPORT, table);
    const cleared = applyLabPart(once, { ...table, rows: [] });
    expect(once.table?.rows).toHaveLength(2);
    expect(cleared.table?.rows).toHaveLength(0);
  });
  it("shows a report only once the Environment has said something about a practical", () => {
    expect(hasReport(EMPTY_REPORT)).toBe(false);
    expect(hasReport(applyLabPart(EMPTY_REPORT, steps))).toBe(true);
  });
  it("writes plain text that names what is the model's and what is the student's", () => {
    const t = reportText("Hooke's law", full(), { ...NO_WRITING, conclusion: "Extension grows with load." });
    expect(t).toContain("Aim: To find how the extension depends on the load.");
    expect(t).toContain("1. Hang a load.");
    expect(t).toContain("Load (N) | Extension (m)");
    expect(t).toContain("4.0 | 0.080");
    expect(t).toContain("Conclusion\nExtension grows with load.");
    expect(t).toContain("Observations\n(not written yet)");
    expect(t).toContain("your own words");
  });
  it("makes a safe file name", () => {
    expect(reportFileName("Hooke's law: how does a spring stretch?")).toBe("lab-report-hooke-s-law-how-does-a-spring-stretch.txt");
    expect(reportFileName("???")).toBe("lab-report-environment.txt");
  });
});

describe("LabReport", () => {
  it("shows the recorded rows and keeps the student's writing out of the model's parts", () => {
    render(<LabReport title="Hooke's law" data={full()} />);
    expect(screen.getByText("0.080")).toBeTruthy();
    expect(screen.getByText("Procedure")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Conclusion"), { target: { value: "It is proportional." } });
    expect((screen.getByLabelText("Conclusion") as HTMLTextAreaElement).value).toBe("It is proportional.");
    expect(screen.getByText(/stay in this browser and are not checked/)).toBeTruthy();
  });
  it("says there are no rows yet and tells the student how to add one", () => {
    render(<LabReport title="Hooke's law" data={applyLabPart(EMPTY_REPORT, { ...table, rows: [] })} />);
    expect(screen.getByText(/No rows yet/)).toBeTruthy();
  });
  it("renders everything as text, never as markup", () => {
    render(<LabReport title="<img src=x onerror=alert(1)>" data={applyLabPart(EMPTY_REPORT, { ...steps, steps: ["<script>alert(1)</script>"] })} />);
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
  });
  it("has controls of at least the 44 px button class", () => {
    render(<LabReport title="t" data={full()} />);
    for (const b of screen.getAllByRole("button")) expect(b.className).toContain("btn");
  });
});
