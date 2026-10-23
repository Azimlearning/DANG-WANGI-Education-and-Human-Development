"use client";

// Ported from Synapse v3: frontend/components/Mascot.tsx (Genui monorepo, commit 835a2cefda28). Read in full and kept as drawn: Axi, the logomark node given a face.
// Flat fills on the Synapse palette; the body is the one place a subtle functional gradient is allowed (V3 BRAND.md section 4). Decorative, so hidden from
// assistive technology; the meaning is always also in text next to it.
import { useId } from "react";

export type MascotMood = "happy" | "thinking" | "celebrate" | "oops";

const INK = "#14312c"; // the face ink, a deep teal-black

export function Mascot({ mood = "happy", size = 96, className = "", bob = true }: { mood?: MascotMood; size?: number; className?: string; bob?: boolean }) {
  const celebrate = mood === "celebrate";
  const id = useId();
  const bodyFill = `url(#mascot-body-${id})`;
  const dx = mood === "thinking" ? 1.5 : 0;
  const dy = mood === "thinking" ? -2.5 : mood === "oops" ? 1.5 : 0;

  return (
    <span className={`inline-block shrink-0 ${bob ? "mascot-bob" : ""} ${className}`} style={{ width: size, height: size }} aria-hidden>
      <svg viewBox="0 0 100 100" width={size} height={size} fill="none">
        <defs>
          <linearGradient id={`mascot-body-${id}`} x1="0" y1="0" x2="0.35" y2="1">
            <stop offset="0%" stopColor="#16b6a3" />
            <stop offset="100%" stopColor="#0a776b" />
          </linearGradient>
        </defs>
        <ellipse cx="50" cy="52" rx="46" ry="16.5" stroke="#12a594" strokeWidth="3" transform="rotate(-18 50 52)" opacity="0.9" />
        <circle cx="93" cy="38" r="4" fill="#12a594" />
        <ellipse cx="42" cy="83" rx="6" ry="4" fill="#0e8a7c" />
        <ellipse cx="58" cy="83" rx="6" ry="4" fill="#0e8a7c" />
        {celebrate ? (
          <>
            <ellipse cx="24" cy="40" rx="5" ry="8" fill="#12a594" transform="rotate(-32 24 40)" />
            <ellipse cx="76" cy="40" rx="5" ry="8" fill="#12a594" transform="rotate(32 76 40)" />
          </>
        ) : (
          <>
            <ellipse cx="24" cy="63" rx="5" ry="8" fill="#12a594" transform="rotate(-14 24 63)" />
            <ellipse cx="76" cy="63" rx="5" ry="8" fill="#12a594" transform="rotate(14 76 63)" />
          </>
        )}
        <circle cx="50" cy="56" r="27" fill={bodyFill} />
        <ellipse cx="50" cy="63" rx="17" ry="13" fill="#3dc2b2" opacity="0.9" />
        <ellipse cx="33" cy="61" rx="4.2" ry="2.7" fill="#f4a28c" opacity="0.55" />
        <ellipse cx="67" cy="61" rx="4.2" ry="2.7" fill="#f4a28c" opacity="0.55" />
        {celebrate ? (
          <>
            <path d="M36 54 q5 -6 10 0" stroke={INK} strokeWidth="2.6" strokeLinecap="round" />
            <path d="M54 54 q5 -6 10 0" stroke={INK} strokeWidth="2.6" strokeLinecap="round" />
          </>
        ) : (
          <>
            <ellipse cx="42" cy="53" rx="7" ry="8" fill="#ffffff" />
            <ellipse cx="58" cy="53" rx="7" ry="8" fill="#ffffff" />
            <circle cx={42 + dx} cy={53 + dy} r="3.4" fill={INK} />
            <circle cx={58 + dx} cy={53 + dy} r="3.4" fill={INK} />
            <circle cx={40.6 + dx} cy={51 + dy} r="1.3" fill="#ffffff" />
            <circle cx={56.6 + dx} cy={51 + dy} r="1.3" fill="#ffffff" />
          </>
        )}
        {mood === "happy" && <path d="M45 63 q5 5 10 0" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />}
        {mood === "celebrate" && <path d="M44 62 q6 8 12 0 z" fill={INK} />}
        {mood === "thinking" && <ellipse cx="50" cy="64" rx="2.6" ry="2.2" fill={INK} />}
        {mood === "oops" && <path d="M45 64 q3 -3 5 0 q2 3 5 0" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />}
        {mood === "thinking" && (
          <>
            <circle cx="74" cy="33" r="2.2" fill="#838e88" />
            <circle cx="80" cy="27" r="2.8" fill="#838e88" />
            <circle cx="87" cy="20" r="3.4" fill="#838e88" />
          </>
        )}
        {mood === "oops" && <path d="M72 34 q3 5 0 7 q-3 -2 0 -7 z" fill="#7fb0d4" />}
        {celebrate && (
          <>
            <path d="M16 24l1.4 3.4L21 29l-3.4 1.4L16 34l-1.4-3.6L11 29l3.6-1.6z" fill="#e6a200" />
            <path d="M84 58l1.1 2.7L88 62l-2.9 1.1L84 66l-1.1-2.9L80 62l2.9-1.3z" fill="#1fa35b" />
          </>
        )}
      </svg>
    </span>
  );
}
