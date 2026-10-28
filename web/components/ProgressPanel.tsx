"use client";

import { useCallback, useEffect, useState } from "react";
import { useT, type StringKey } from "../lib/i18n";
import { decode, empty, encode, list, load, mastery, save, type Progress } from "../lib/progress";

const MASTERY: Record<string, StringKey> = { "Just started": "masteryJustStarted", Secure: "masterySecure", "Getting there": "masteryGettingThere" };

/** "My progress": what this device remembers about concept checks. Kept in this browser only; the export code moves it to another device. */
export function ProgressPanel({ bare = false }: { bare?: boolean } = {}) {
  const t = useT();
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
  const button = "btn btn-ghost px-4 text-sm";
  const field = "rounded-ctl border-2 border-line-2 bg-card p-2 text-ink";

  const body = (
      <div className="grid gap-3 pt-2 text-sm">
        <p className="text-ink-dim">{t("progressKept")}</p>
        {items.length === 0 ? (
          <p>{t("progressNothing")}</p>
        ) : (
          <ul className="grid gap-2">
            {items.map((e) => (
              <li key={e.id} className="rounded-ctl border-2 border-line p-3">
                <strong>{e.title}</strong>
                <br />
                {t("progressRow", { mastery: t(MASTERY[mastery(e)] ?? "masteryGettingThere"), correct: e.correct, tries: e.tries })}
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" className={button} onClick={() => { setShown(encode(state)); setMessage(t("codeShown")); }}>
            {t("showCode")}
          </button>
          <button
            type="button"
            className={button}
            onClick={() => {
              if (!confirmClear) { setConfirmClear(true); return; }
              save(empty());
              setState(empty());
              setConfirmClear(false);
              setMessage(t("progressCleared"));
            }}
          >
            {confirmClear ? t("pressAgain") : t("clearProgress")}
          </button>
        </div>
        {shown ? <textarea readOnly aria-label={t("codeAria")} value={shown} rows={3} className={field} onFocus={(e) => e.currentTarget.select()} /> : null}
        <label htmlFor="progress-import" className="font-semibold">
          {t("loadCodeLabel")}
        </label>
        <textarea id="progress-import" value={code} onChange={(e) => setCode(e.target.value)} rows={2} className={field} />
        <button
          type="button"
          className={button}
          disabled={!code.trim()}
          onClick={() => {
            const got = decode(code);
            if (!got) { setMessage(t("invalidCode")); return; }
            save(got);
            setState(got);
            setCode("");
            setMessage(t("progressLoaded"));
          }}
        >
          {t("loadCode")}
        </button>
        <p role="status">{message}</p>
      </div>
  );

  if (bare) {
    return (
      <section aria-label={t("myProgress")} className="study-card grid gap-2 p-4">
        <h2 className="font-display text-lg font-semibold">{t("progressTitle", { n: items.length })}</h2>
        {body}
      </section>
    );
  }
  return (
    <details className="study-card p-3">
      <summary className="min-h-11 cursor-pointer py-2 font-display font-semibold">{t("progressTitle", { n: items.length })}</summary>
      {body}
    </details>
  );
}
