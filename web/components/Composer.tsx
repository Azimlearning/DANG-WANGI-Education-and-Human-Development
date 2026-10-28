"use client";

// Adapted from Synapse v3: frontend/components/chat/Composer.tsx (Genui monorepo, commit 835a2cefda28). "hero" is the big front-door prompt, "bar" the pinned
// composer once a conversation is going. Kept the same logic; the field is `#q` and the button is a submit "Ask" (the browser smoke drives both), the limit is the
// API's 500 characters, and the button says "Ask" not "Build it": a covered question is answered from the library and nothing is built.
import { useState } from "react";
import { useT } from "../lib/i18n";

export function Composer({ onSend, disabled, variant = "bar" }: { onSend: (message: string) => void; disabled: boolean; variant?: "bar" | "hero" }) {
  const t = useT();
  const [value, setValue] = useState("");
  const hero = variant === "hero";

  const submit = () => {
    const message = value.trim();
    if (!message || disabled) return;
    setValue("");
    onSend(message);
  };

  return (
    <form
      className={hero ? "flex items-stretch gap-3" : "flex items-end gap-2.5 pb-5 pt-2"}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label htmlFor="q" className="sr-only">
        {t("askLabel")}
      </label>
      <textarea
        id="q"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={1}
        maxLength={500}
        autoComplete="off"
        placeholder={hero ? t("placeholderHero") : t("placeholderBar")}
        className={`composer-field w-0 min-w-0 flex-1 resize-none rounded-card border-2 border-line-2 bg-card text-ink outline-none placeholder:text-ink-faint focus:border-primary focus:ring-4 focus:ring-primary-soft ${
          hero ? "min-h-[58px] px-5 py-4 text-lg font-semibold" : "min-h-[48px] px-4 py-3 text-[16px] font-medium"
        }`}
      />
      <button type="submit" disabled={disabled || value.trim().length === 0} className={`btn btn-primary ${hero ? "px-7 text-base" : "min-h-[48px] px-5 text-[15px]"}`}>
        {disabled ? t("asking") : t("askButton")}
      </button>
    </form>
  );
}
