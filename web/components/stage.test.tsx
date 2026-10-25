import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { EnvironmentBlock } from "@synapse/schema";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Stage } from "./Stage";

afterEach(cleanup);

const block = {
  id: "env1",
  title: "Hooke's law",
  label: "model-checked",
  lane: "instantiate",
  html: "<p>x</p>",
  htmlSha256: "0".repeat(64),
  kitVersion: "0.1.0",
  planSummary: "A spring.",
  citations: [{ source: "textbook-physics-physics-f5-removed", page: 36, quote: null, verified: false }],
  checked: { layers: ["scan"], controlsExercised: 1, gridPoints: 0, referenceCases: 0, readouts: 1, models: [], limits: "x" },
} as unknown as EnvironmentBlock;

describe("Present mode", () => {
  it("is off until asked, says Presenting when on, and keeps the label, the lane and the source visible", () => {
    render(<Stage block={block} onBack={vi.fn()} />);
    expect(screen.queryByText("Presenting")).toBeNull();
    expect(screen.getByLabelText("Where this Environment comes from")).toBeTruthy();
    fireEvent.click(screen.getByText("Present"));
    expect(screen.getByText("Presenting")).toBeTruthy();
    expect(screen.getByText("Checked by code")).toBeTruthy();
    expect(screen.getByText("From the library")).toBeTruthy();
    expect(screen.getByTestId("present-source").textContent).toContain("KSSM Physics Form 5 textbook, PDF page 36");
  });

  it("folds the long provenance away, keeps it mounted, and stops presenting on the same button", () => {
    render(<Stage block={block} onBack={vi.fn()} />);
    fireEvent.click(screen.getByText("Present"));
    expect(screen.getByLabelText("Where this Environment comes from").parentElement?.className).toContain("hidden");
    fireEvent.click(screen.getByText("Stop presenting"));
    expect(screen.getByLabelText("Where this Environment comes from").parentElement?.className).not.toContain("hidden");
    expect(screen.queryByTestId("present-source")).toBeNull();
  });

  it("reports its state to assistive technology and is at least the 44 px button class", () => {
    render(<Stage block={block} onBack={vi.fn()} />);
    const button = screen.getByText("Present");
    expect(button.getAttribute("aria-pressed")).toBe("false");
    expect(button.className).toContain("btn");
    fireEvent.click(button);
    expect(screen.getByText("Stop presenting").getAttribute("aria-pressed")).toBe("true");
  });
});
