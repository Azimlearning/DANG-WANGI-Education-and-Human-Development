// The exam mirror's marker (W5c). A point is earned when every stem of at least one wording is in the answer; a stem made only of digits must equal a whole number in
// the answer, any other stem matches a word that starts with it. Words are runs of letters and digits, lower-cased. Same answer, same score; no model, nothing is sent
// anywhere. api/models/exam.py holds the same rule for checking the data, and both are tested against the same vectors.
import type { ExamEvent } from "@synapse/schema";

export function words(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

const stemIn = (stem: string, ws: string[]): boolean => (/^[0-9]+$/.test(stem) ? ws.includes(stem) : ws.some((w) => w.startsWith(stem)));

export function earned(point: ExamEvent["points"][number], answer: string): boolean {
  const ws = words(answer);
  return point.wordings.some((wording) => wording.every((s) => stemIn(s, ws)));
}

export function mark(item: Pick<ExamEvent, "points">, answer: string): { score: number; got: boolean[] } {
  const got = item.points.map((p) => earned(p, answer));
  return { score: got.filter(Boolean).length, got };
}
