import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { EnvironmentBlock } from "@synapse/schema";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LabelBadge, LaneBadge } from "./Badges";
import { Composer } from "./Composer";
import { DegradedCard } from "./DegradedCard";
import { ProgressStages } from "./ProgressStages";
import { QuickStarts, STARTERS } from "./SideRail";

afterEach(cleanup);

describe("honest badges", () => {
  it("gives the green check only to kit-verified, and says outright when a model wrote the page whole", () => {
    const labels: EnvironmentBlock["label"][] = ["kit-verified", "model-checked", "reviewed", "canonical"];
    const classes = labels.map((label) => {
      const { container, unmount } = render(<LabelBadge label={label} />);
      const cls = (container.firstElementChild as HTMLElement).className;
      unmount();
      return cls;
    });
    expect(classes[0]).toContain("study-badge-verified");
    expect(classes[1]).toContain("study-badge-checked");
    expect(classes[1]).not.toContain("study-badge-verified");
    render(<LaneBadge lane="free" />);
    expect(screen.getByText("Written whole by a model").className).toContain("study-badge-free");
  });

  it("never names the label with more than the trust ladder allows", () => {
    render(<LabelBadge label="model-checked" />);
    expect(screen.getByText("Checked by code")).toBeTruthy();
    expect(screen.queryByText(/verified/i)).toBeNull();
  });
});

describe("progress", () => {
  it("shows the real steps with the current one marked working and no code preview", () => {
    render(<ProgressStages step="planning" />);
    expect(screen.getByRole("status").textContent).toContain("3 of 5");
    expect(screen.getAllByText("Designing the experiment").length).toBeGreaterThan(0);
    expect(screen.getAllByText("done")).toHaveLength(2);
    expect(screen.getAllByText("working")).toHaveLength(1);
    expect(screen.queryByText(/code being written/i)).toBeNull();
  });
});

describe("composer", () => {
  it("submits a trimmed question with Enter, keeps Shift+Enter for a new line, and is limited to the API's 500 characters", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled={false} />);
    const box = screen.getByLabelText("Ask a science question") as HTMLTextAreaElement;
    expect(box.id).toBe("q");
    expect(box.maxLength).toBe(500);
    fireEvent.change(box, { target: { value: "  Why does ice float?  " } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("Why does ice float?");
    expect(box.value).toBe("");
  });

  it("cannot be submitted when empty or while a question is being asked", () => {
    const onSend = vi.fn();
    const { rerender } = render(<Composer onSend={onSend} disabled={false} />);
    expect((screen.getByRole("button", { name: "Ask" }) as HTMLButtonElement).disabled).toBe(true);
    rerender(<Composer onSend={onSend} disabled />);
    fireEvent.change(screen.getByLabelText("Ask a science question"), { target: { value: "x" } });
    expect((screen.getByRole("button", { name: "Asking…" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("degraded card", () => {
  it("is an alert for an error and a status for a note, and offers a retry only when given one", () => {
    const retry = vi.fn();
    const { rerender } = render(<DegradedCard kind="error" message="Could not reach the server." onRetry={retry} />);
    expect(screen.getByRole("alert").textContent).toContain("Could not reach the server.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledTimes(1);
    rerender(<DegradedCard kind="note" message="Written answer only." />);
    expect(screen.getByRole("status").textContent).toContain("Written answer only.");
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("quick starts", () => {
  it("offers the questions the library answers and sends the one that is pressed", () => {
    const onPrompt = vi.fn();
    render(<QuickStarts onPrompt={onPrompt} disabled={false} />);
    expect(screen.getAllByRole("button")).toHaveLength(STARTERS.length);
    fireEvent.click(screen.getByText(STARTERS[1] as string));
    expect(onPrompt).toHaveBeenCalledWith(STARTERS[1]);
  });
});
