"use client";

// The progress bar's pacing. The server's stages are true, but a stored lab answers in a few milliseconds and the bar would flash by unseen, so the bar a student sees
// moves forward one stage at a time, at most one every STEP_MS, until it catches up with the real stage. A slow question (a lab being made) is never delayed: the bar is
// already where the server is. It only ever moves forward, and it only runs while a turn is open.
import { useEffect, useState } from "react";
import { STEPS, type StepKey } from "./turns";

export const STEP_MS = 280;

const index = (k: StepKey) => STEPS.findIndex((s) => s.key === k);

/** The stage to draw: `real` once the bar has caught up, else one stage after the one drawn last. */
export function nextShown(shown: StepKey, real: StepKey): StepKey {
  const from = index(shown);
  const to = index(real);
  if (to <= from) return shown;
  return STEPS[from + 1]?.key ?? shown;
}

/** The stage the bar shows for a turn whose real stage is `real`. `key` restarts the bar for a new question. */
export function usePacedStep(real: StepKey, key: number): StepKey {
  const [shown, setShown] = useState<{ key: number; step: StepKey }>({ key, step: "reading" });
  const current = shown.key === key ? shown.step : "reading";
  useEffect(() => {
    if (shown.key !== key) {
      setShown({ key, step: "reading" });
      return;
    }
    if (index(shown.step) >= index(real)) return;
    const id = setTimeout(() => setShown({ key, step: nextShown(shown.step, real) }), STEP_MS);
    return () => clearTimeout(id);
  }, [shown, real, key]);
  return current;
}
