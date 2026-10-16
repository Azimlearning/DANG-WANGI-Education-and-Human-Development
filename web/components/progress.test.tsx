import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { STORAGE_KEY, encode, empty, record } from "../lib/progress";
import { ProgressPanel } from "./ProgressPanel";

beforeEach(() => localStorage.clear());
afterEach(cleanup);

const seeded = () => record(record(empty(), { id: "spring-1", title: "Hooke's law" }, "correct", new Date(1)), { id: "spring-1", title: "Hooke's law" }, "correct", new Date(2));

describe("ProgressPanel", () => {
  it("says so when there is nothing yet, and lists what the device remembers", () => {
    render(<ProgressPanel />);
    expect(screen.getByText(/Nothing yet/)).toBeTruthy();
    cleanup();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded()));
    render(<ProgressPanel />);
    expect(screen.getByText("Hooke's law")).toBeTruthy();
    expect(screen.getByText(/Secure: 2 right out of 2/)).toBeTruthy();
  });

  it("refreshes when an Environment records an answer", async () => {
    render(<ProgressPanel />);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded()));
    window.dispatchEvent(new Event("synapse-progress"));
    await waitFor(() => expect(screen.getByText("Hooke's law")).toBeTruthy());
  });

  it("shows a code that loads back, rejects a bad one, and clears only on the second press", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded()));
    render(<ProgressPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Show my code" }));
    const code = (screen.getByLabelText("Your progress code") as HTMLTextAreaElement).value;
    expect(code).toBe(encode(seeded()));

    fireEvent.click(screen.getByRole("button", { name: "Clear progress" }));
    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull(); // one press does not clear
    fireEvent.click(screen.getByRole("button", { name: "Press again to clear" }));
    await waitFor(() => expect(screen.getByText(/Nothing yet/)).toBeTruthy());

    fireEvent.change(screen.getByLabelText("Load a progress code"), { target: { value: "SYN1.broken.00000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Load code" }));
    expect(screen.getByRole("status").textContent).toMatch(/not valid/);

    fireEvent.change(screen.getByLabelText("Load a progress code"), { target: { value: code } });
    fireEvent.click(screen.getByRole("button", { name: "Load code" }));
    await waitFor(() => expect(screen.getByText("Hooke's law")).toBeTruthy());
  });
});
