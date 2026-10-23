import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import type { EnvironmentBlock } from "@synapse/schema";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sha256Hex } from "../lib/hash";
import { THEME_EVENT } from "../lib/theme";
import { EnvironmentFrame } from "./EnvironmentFrame";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  delete document.documentElement.dataset.theme;
});

async function block(): Promise<EnvironmentBlock> {
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
    citations: [{ source: "UNVERIFIED", page: null, quote: null, verified: false }],
    checked: { layers: ["scan"], controlsExercised: 1, gridPoints: 0, referenceCases: 0, readouts: 1, models: [], limits: "Checked by code." },
    planSummary: "A fixture.",
  };
}

/** Replace what every iframe's `contentWindow` returns BEFORE rendering, so the frame's own first `load` (jsdom fires one when the iframe is inserted, as a browser
 *  does) is observed. */
function stubFrameWindow() {
  const post = vi.fn();
  vi.spyOn(HTMLIFrameElement.prototype, "contentWindow", "get").mockReturnValue({ postMessage: post } as unknown as Window);
  return post;
}

describe("EnvironmentFrame and the theme", () => {
  it("tells the frame the theme when it loads and again whenever the theme changes, with the one message shape and nothing else", async () => {
    const post = stubFrameWindow();
    document.documentElement.dataset.theme = "dark";
    render(<EnvironmentFrame block={await block()} height={300} />);
    await waitFor(() => expect(post).toHaveBeenCalledWith({ type: "synapse_theme", theme: "dark" }, "*"));
    document.documentElement.dataset.theme = "light";
    window.dispatchEvent(new Event(THEME_EVENT));
    expect(post).toHaveBeenLastCalledWith({ type: "synapse_theme", theme: "light" }, "*");
    expect(post.mock.calls.every(([message, target]) => Object.keys(message as object).sort().join() === "theme,type" && target === "*")).toBe(true);
  });

  it("tells a frame that has left its own document nothing (it is being torn down)", async () => {
    const post = stubFrameWindow();
    document.documentElement.dataset.theme = "dark";
    const onRefused = vi.fn();
    const { container } = render(<EnvironmentFrame block={await block()} height={300} onRefused={onRefused} />);
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1)); // its own first load: told the theme
    const frame = container.querySelector("iframe") as HTMLIFrameElement;
    fireEvent.load(frame); // a second load is a navigation away
    window.dispatchEvent(new Event(THEME_EVENT));
    expect(onRefused).toHaveBeenCalled();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("stops listening when the frame is removed", async () => {
    const post = stubFrameWindow();
    const { unmount } = render(<EnvironmentFrame block={await block()} height={300} />);
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    unmount();
    window.dispatchEvent(new Event(THEME_EVENT));
    expect(post).toHaveBeenCalledTimes(1);
  });
});
