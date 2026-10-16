import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EnvironmentBlock } from "@synapse/schema";
import { sha256Hex } from "../lib/hash";
import { EnvironmentFrame } from "./EnvironmentFrame";
import { MAX_PEEK_ACTIONS, Peek } from "./Peek";
import { Stage } from "./Stage";

afterEach(cleanup);

async function makeBlock(over: Partial<EnvironmentBlock> = {}): Promise<EnvironmentBlock> {
  const html = "<!doctype html><html><body><p>spring</p></body></html>";
  return {
    type: "Environment",
    id: "reference-spring-abc",
    meta: { status: "ready", error: null },
    title: "Why does a spring stretch?",
    lane: "instantiate",
    label: "model-checked",
    kitVersion: "0.0.1",
    htmlSha256: await sha256Hex(html),
    html,
    citations: [{ source: "UNVERIFIED (corpus not loaded until P2)", page: null, quote: null, verified: false }],
    checked: { layers: ["postprocess", "scan", "render"], controlsExercised: 1, gridPoints: 0, referenceCases: 0, readouts: 1, models: [{ id: "mechanics.hookes", params: { k: 50 } }], limits: "Checked by code, not by a person." },
    planSummary: "A hand-written fixture.",
    ...over,
  };
}

describe("EnvironmentFrame", () => {
  it("renders a verified block in an iframe whose sandbox is exactly allow-scripts", async () => {
    const block = await makeBlock();
    const { container } = render(<EnvironmentFrame block={block} height={300} />);
    await waitFor(() => expect(container.querySelector("iframe")).not.toBeNull());
    const frame = container.querySelector("iframe")!;
    expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
    expect(frame.getAttribute("srcdoc")).toBe(block.html);
    expect(frame.getAttribute("allow")).toBeNull();
  });

  it("refuses to render when the hash does not match, and shows why", async () => {
    const block = await makeBlock({ htmlSha256: "0".repeat(64) });
    const onRefused = vi.fn();
    const { container } = render(<EnvironmentFrame block={block} height={300} onRefused={onRefused} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(container.querySelector("iframe")).toBeNull();
    expect(screen.getByRole("alert").textContent).toMatch(/does not match the hash/);
    expect(onRefused).toHaveBeenCalledOnce();
  });

  it("refuses when the html is changed by one character after hashing", async () => {
    const block = await makeBlock();
    const { container } = render(<EnvironmentFrame block={{ ...block, html: block.html.replace("spring", "sprinG") }} height={300} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("closes the frame when it loads a second time, which means it navigated away", async () => {
    const block = await makeBlock();
    const { container } = render(<EnvironmentFrame block={block} height={300} />);
    await waitFor(() => expect(container.querySelector("iframe")).not.toBeNull());
    const frame = container.querySelector("iframe")!;
    // jsdom fires its own `load` for the srcdoc when the iframe is inserted (a browser does too): that is the first, expected load.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container.querySelector("iframe")).not.toBeNull();
    fireEvent.load(frame); // a further load means the frame navigated
    await waitFor(() => expect(container.querySelector("iframe")).toBeNull());
    expect(screen.getByRole("alert").textContent).toMatch(/navigate away/);
  });

  it("shows an error the Environment reports through the bridge, only from its own frame", async () => {
    const block = await makeBlock();
    const { container } = render(<EnvironmentFrame block={block} height={300} />);
    await waitFor(() => expect(container.querySelector("iframe")).not.toBeNull());
    const frame = container.querySelector("iframe")!;
    window.dispatchEvent(new MessageEvent("message", { data: { type: "synapse_error", message: "forged" }, source: window }));
    expect(screen.queryByText(/forged/)).toBeNull();
    window.dispatchEvent(new MessageEvent("message", { data: { type: "synapse_error", message: "boom" }, source: frame.contentWindow }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/boom/));
  });
});

describe("the Kit's self-check", () => {
  it("closes the frame when its own frame reports a violation, and ignores one from anywhere else", async () => {
    const block = await makeBlock();
    const { container } = render(<EnvironmentFrame block={block} height={300} />);
    await waitFor(() => expect(container.querySelector("iframe")).not.toBeNull());
    const frame = container.querySelector("iframe")!;
    window.dispatchEvent(new MessageEvent("message", { data: { type: "synapse_violation", problems: ["x"] }, source: window }));
    expect(container.querySelector("iframe")).not.toBeNull();
    window.dispatchEvent(new MessageEvent("message", { data: { type: "synapse_violation", problems: ["readout shows 42.000 m"] }, source: frame.contentWindow }));
    await waitFor(() => expect(container.querySelector("iframe")).toBeNull());
    expect(screen.getByRole("alert").textContent).toMatch(/closed/);
  });
});

describe("Peek and Stage", () => {
  it("Peek has at most two actions and states its provenance", async () => {
    const block = await makeBlock();
    const onOpen = vi.fn();
    const { container } = render(<Peek block={block} onOpen={onOpen} />);
    const actions = container.querySelectorAll("button, a[href]");
    expect(actions.length).toBeLessThanOrEqual(MAX_PEEK_ACTIONS);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(onOpen).toHaveBeenCalledOnce();
    expect(screen.getByText(/Checked by code, no verified textbook source/)).toBeTruthy();
    expect(screen.getByText(/What was checked/)).toBeTruthy();
    expect(screen.getByText(/Science model: mechanics.hookes \(k = 50\)/)).toBeTruthy();
    expect(screen.getByText(/Instantiate/)).toBeTruthy();
    expect(screen.getByText(/not verified/)).toBeTruthy();
    expect(screen.getByText(/Checked by code, not by a person\./)).toBeTruthy();
  });

  it("Stage is a dialog with a Back button that also closes on Escape", async () => {
    const block = await makeBlock();
    const onBack = vi.fn();
    render(<Stage block={block} onBack={onBack} />);
    expect(screen.getByRole("dialog")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onBack).toHaveBeenCalledTimes(2);
  });
});
