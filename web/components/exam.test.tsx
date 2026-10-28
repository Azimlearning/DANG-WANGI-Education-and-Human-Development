import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ExamEvent } from "@synapse/schema";
import { afterEach, describe, expect, it } from "vitest";
import { mark, words } from "../lib/exam";
import { parseStreamEvent } from "../lib/stream";
import { turnReducer } from "../lib/turns";
import { ExamCard } from "./ExamCard";

afterEach(cleanup);

const item: ExamEvent = {
  type: "exam",
  id: "wave-speed-short",
  stem: "A wave has a frequency of 50 Hz and a wavelength of 2 m. State how the speed is found, show the substitution and give the speed.",
  marks: 3,
  points: [
    { text: "Speed equals frequency multiplied by wavelength.", wordings: [["speed", "frequen", "wavelength"], ["v", "f", "wavelength"]] },
    { text: "The substitution uses 50 and 2.", wordings: [["50", "2"]] },
    { text: "The speed is 100 m/s.", wordings: [["100"]] },
  ],
  sample: "Wave speed equals frequency multiplied by wavelength. Speed = 50 x 2 = 100 m/s.",
};

describe("the marker (the same vectors as api/models/test_exam.py)", () => {
  it("splits words on letters and digits and ignores case", () => {
    expect(words("THE Speed, is 100 m/s!")).toEqual(["the", "speed", "is", "100", "m", "s"]);
  });
  it("earns every mark for the sample answer and none for an empty answer", () => {
    expect(mark(item, item.sample)).toEqual({ score: 3, got: [true, true, true] });
    expect(mark(item, "")).toEqual({ score: 0, got: [false, false, false] });
  });
  it("needs a whole number for a digit stem", () => {
    expect(mark(item, "the speed is 1000").got[2]).toBe(false);
    expect(mark(item, "the speed is 100").got[2]).toBe(true);
  });
  it("gives a wrong total the points it earned and no more", () => {
    expect(mark(item, "speed = frequency x wavelength = 50 x 2 = 200 m/s")).toEqual({ score: 2, got: [true, true, false] });
  });
  it("gives the same score for the same text, and never more than the total", () => {
    expect(mark(item, item.sample + item.sample).score).toBe(3);
    expect(mark(item, "Frequency and wavelength")).toEqual(mark(item, "Frequency and wavelength"));
  });
  it("matches a word that starts with the stem", () => {
    const p = { points: [{ text: "x", wordings: [["proportion"]] }] };
    expect(mark(p, "directly proportional").score).toBe(1);
    expect(mark(p, "inversely related").score).toBe(0);
  });
});

describe("ExamCard", () => {
  it("does not mark until asked, and cannot mark an empty answer", () => {
    render(<ExamCard item={item} />);
    expect((screen.getByText("Mark my answer") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByTestId("exam-score")).toBeNull();
  });
  it("shows the score as words, each point earned or missed, and the full-mark answer", () => {
    render(<ExamCard item={item} />);
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "speed = frequency x wavelength = 50 x 2 = 200 m/s" } });
    fireEvent.click(screen.getByText("Mark my answer"));
    expect(screen.getByTestId("exam-score").textContent).toBe("2 of 3 marks");
    expect(screen.getAllByText(/Earned:/)).toHaveLength(2);
    expect(screen.getAllByText(/Missed:/)).toHaveLength(1);
    expect(screen.getByText(/A full-mark answer:/)).toBeTruthy();
  });
  it("locks the answer after marking, says what keyword marking is, and can be hidden", () => {
    render(<ExamCard item={item} />);
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "100" } });
    fireEvent.click(screen.getByText("Mark my answer"));
    expect((screen.getByLabelText("Your answer") as HTMLTextAreaElement).readOnly).toBe(true);
    expect(screen.getByText(/not by a teacher/)).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Hide this exam practice"));
    expect(screen.queryByTestId("exam")).toBeNull();
  });
  it("renders the question as text, never as markup", () => {
    render(<ExamCard item={{ ...item, stem: "<img src=x onerror=alert(1)> what is the speed of the wave described here?" }} />);
    expect(document.querySelector("img")).toBeNull();
  });
});

describe("the exam item on the wire and in a turn", () => {
  it("is parsed when well formed and dropped when marks do not match the points or a stem is not a plain word stem", () => {
    expect(parseStreamEvent(item)).toEqual(item);
    expect(parseStreamEvent({ ...item, marks: 4 })).toBeNull();
    expect(parseStreamEvent({ ...item, points: [item.points[0]] })).toBeNull();
    expect(parseStreamEvent({ ...item, points: [item.points[0], { text: "x", wordings: [["Has Space"]] }] })).toBeNull();
    expect(parseStreamEvent({ ...item, points: [item.points[0], { text: "x", wordings: [[]] }] })).toBeNull();
  });
  it("lands on the current turn and nowhere else", () => {
    let turns = turnReducer([], { type: "ask", question: "q1" });
    turns = turnReducer(turns, { type: "event", event: item });
    turns = turnReducer(turns, { type: "ask", question: "q2" });
    expect(turns[0]?.exam).toEqual(item);
    expect(turns[1]?.exam).toBeNull();
  });
});

describe("the fermentation item (the same vectors as api/models/test_exam.py)", () => {
  const f: ExamEvent = {
    type: "exam",
    id: "yeast-fermentation-limewater",
    stem: "Yeast is mixed with glucose solution in tube A. Tube B has glucose solution only and is the control. State one observation in limewater A after 60 minutes and explain your answer.",
    marks: 2,
    points: [
      { text: "Limewater A turns milky or cloudy.", wordings: [["milky"], ["cloudy"], ["turn", "chalky"]] },
      { text: "The yeast produces carbon dioxide during fermentation.", wordings: [["carbon", "dioxid"], ["co2"]] },
    ],
    sample: "Limewater A turns milky. The yeast ferments the glucose and produces carbon dioxide, which turns the limewater milky.",
  };
  it("marks the observation and the gas separately", () => {
    expect(mark(f, f.sample)).toEqual({ score: 2, got: [true, true] });
    expect(mark(f, "Limewater A turns cloudy.")).toEqual({ score: 1, got: [true, false] });
    expect(mark(f, "The yeast produces CO2 as it ferments.")).toEqual({ score: 1, got: [false, true] });
    expect(mark(f, "Limewater A stays clear.")).toEqual({ score: 0, got: [false, false] });
  });
});
