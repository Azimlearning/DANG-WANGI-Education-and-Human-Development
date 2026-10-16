"use client";

import { useCallback, useEffect, useState } from "react";
import { decode, empty, encode, list, load, mastery, save, type Progress } from "../lib/progress";

/** "My progress": what this device remembers about concept checks. Kept in this browser only; the export code moves it to another device. */
export function ProgressPanel() {
  const [state, setState] = useState<Progress>(empty());
  const [code, setCode] = useState("");
  const [shown, setShown] = useState("");
  const [message, setMessage] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  const refresh = useCallback(() => setState(load()), []);
  useEffect(() => {
    refresh();
    window.addEventListener("synapse-progress", refresh);
    return () => window.removeEventListener("synapse-progress", refresh);
  }, [refresh]);

  const items = list(state);
  const button = "min-h-11 min-w-11 rounded-xl px-4 text-sm font-semibold";
  const outline = { border: "1px solid var(--border)" } as const;

  return (
    <details className="rounded-2xl p-3" style={outline}>
      <summary className="min-h-11 cursor-pointer py-2 font-semibold">My progress ({items.length})</summary>
      <div className="grid gap-3 pt-2 text-sm">
        <p style={{ color: "var(--muted)" }}>Kept in this browser only. Nothing is sent anywhere. It counts your first answer to each check question.</p>
        {items.length === 0 ? (
          <p>Nothing yet. Answer a check question in an Environment and it will appear here.</p>
        ) : (
          <ul className="grid gap-2">
            {items.map((e) => (
              <li key={e.id} className="rounded-xl p-3" style={outline}>
                <strong>{e.title}</strong>
                <br />
                {mastery(e)}: {e.correct} right out of {e.tries}
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" className={button} style={outline} onClick={() => { setShown(encode(state)); setMessage("Copy this code to keep your progress or to move it to another device."); }}>
            Show my code
          </button>
          <button
            type="button"
            className={button}
            style={outline}
            onClick={() => {
              if (!confirmClear) { setConfirmClear(true); return; }
              save(empty());
              setState(empty());
              setConfirmClear(false);
              setMessage("Progress cleared on this device.");
            }}
          >
            {confirmClear ? "Press again to clear" : "Clear progress"}
          </button>
        </div>
        {shown ? <textarea readOnly aria-label="Your progress code" value={shown} rows={3} className="rounded-xl p-2" style={{ ...outline, background: "var(--bg)", color: "var(--fg)" }} onFocus={(e) => e.currentTarget.select()} /> : null}
        <label htmlFor="progress-import" className="font-semibold">
          Load a progress code
        </label>
        <textarea id="progress-import" value={code} onChange={(e) => setCode(e.target.value)} rows={2} className="rounded-xl p-2" style={{ ...outline, background: "var(--bg)", color: "var(--fg)" }} />
        <button
          type="button"
          className={button}
          style={outline}
          disabled={!code.trim()}
          onClick={() => {
            const got = decode(code);
            if (!got) { setMessage("That code is not valid. Check that you copied all of it."); return; }
            save(got);
            setState(got);
            setCode("");
            setMessage("Progress loaded. It replaced what this device had.");
          }}
        >
          Load code
        </button>
        <p role="status">{message}</p>
      </div>
    </details>
  );
}
