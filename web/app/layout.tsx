// Ported from Synapse v3: frontend/app/layout.tsx (Genui monorepo, commit 835a2cefda28). Read in full and adapted: the same three self-hosted faces through
// next/font (fetched at build time, served from this origin; no runtime CDN), the same set-the-theme-before-first-paint script, and the CSS variable names
// changed to `--face-*` so the Tailwind 4 theme in globals.css can map them without referring to itself.
import type { Metadata, Viewport } from "next";
import { Fredoka, JetBrains_Mono, Nunito } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";

const display = Fredoka({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--face-display", display: "swap" });
const sans = Nunito({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--face-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--face-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Synapse",
  description: "Verified, interactive science environments for KSSM Form 4 and 5.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// A saved choice wins, else the system preference. The top-bar toggle updates both. Wrapped in try: storage can be blocked, and then the system setting stands.
const themeScript = `try{var t=localStorage.getItem('synapse-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
