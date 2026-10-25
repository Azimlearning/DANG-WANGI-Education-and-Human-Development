// The Kit's one stylesheet, as a module of its own so that `audit.ts` can compare the stylesheet in the page with it. The audit skips its CSS rules for a
// stylesheet only when that element is one `environment()` created AND its text is exactly this string; any other stylesheet, including one a page gave the
// id `syn-style`, or this one after a page edited it, gets the full CSS check (kit-guardian W3: a page-made `syn-style` used to skip it).

export const STYLE = `
:root{--syn-bg:#ffffff;--syn-fg:#2f3a34;--syn-muted:#4f5d57;--syn-accent:#0a776b;--syn-edge:#075247;--syn-card:#f7f8f4;--syn-border:#d3dace;--syn-radius:18px;--syn-indicator:#d6336c;--syn-liquid:#7cc4d8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--syn-bg:#16201c;--syn-fg:#e9efea;--syn-muted:#a4b2ab;--syn-accent:#16b6a3;--syn-edge:#063f38;--syn-card:#0e1512;--syn-border:#34403a;--syn-indicator:#f06595;--syn-liquid:#3b8fa6}}
:root[data-theme="dark"]{--syn-bg:#16201c;--syn-fg:#e9efea;--syn-muted:#a4b2ab;--syn-accent:#16b6a3;--syn-edge:#063f38;--syn-card:#0e1512;--syn-border:#34403a;--syn-indicator:#f06595;--syn-liquid:#3b8fa6}
*{box-sizing:border-box}
body{margin:0;background:var(--syn-bg);color:var(--syn-fg);font:16px/1.5 system-ui,sans-serif}
.syn-env{max-width:720px;margin:0 auto;padding:16px;display:grid;gap:16px}
.syn-env h1{font-size:1.4rem;margin:0}
.syn-note{background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:12px 16px;color:var(--syn-muted)}
.syn-stage{min-height:120px;border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:12px;display:grid;gap:8px}
.syn-controls,.syn-readouts{display:grid;gap:12px}
.syn-control{display:grid;gap:4px}
.syn-control label{font-weight:600}
.syn-control input[type=range]{width:100%;min-height:44px;accent-color:var(--syn-accent)}
.syn-readout{display:flex;justify-content:space-between;align-items:center;min-height:44px;background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 16px}
.syn-readout output{font-weight:700;font-variant-numeric:tabular-nums}
.syn-btn{min-height:44px;min-width:44px;padding:0 16px;border-radius:var(--syn-radius);border:2px solid var(--syn-border);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:600;box-shadow:0 3px 0 var(--syn-border)}
.syn-btn:active{transform:translateY(2px);box-shadow:0 1px 0 var(--syn-border)}
.syn-text{margin:0;color:var(--syn-muted)}
.syn-steps{margin:0;padding-left:1.4rem;display:grid;gap:4px}
.syn-card{background:var(--syn-card);border:2px solid var(--syn-border);border-radius:var(--syn-radius);padding:8px 16px}
.syn-card dl{display:grid;gap:2px;margin:0}
.syn-card dt{font-weight:600}
.syn-card dd{margin:0 0 6px;color:var(--syn-muted)}
.syn-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.syn-graph{width:100%;height:auto;max-height:260px}
.syn-table-wrap{overflow-x:auto;max-width:100%}
.syn-table{border-collapse:collapse;width:100%;table-layout:fixed;font-variant-numeric:tabular-nums}
.syn-table th,.syn-table td{border:1px solid var(--syn-border);padding:4px 6px;text-align:right;overflow-wrap:anywhere;font-size:.875rem}
.syn-masses{display:grid;gap:8px}
.syn-tray,.syn-hanger{display:flex;flex-wrap:wrap;align-items:center;gap:8px;min-height:64px;padding:8px;border-radius:var(--syn-radius)}
.syn-tray{border:2px dashed var(--syn-border)}
.syn-hanger{border:2px solid var(--syn-border);background:var(--syn-card)}
.syn-hanger.syn-over{border-color:var(--syn-accent)}
.syn-cap{flex:0 0 100%;font-size:.75rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--syn-muted)}
.syn-mass{min-width:44px;min-height:44px;padding:0;border-radius:12px;border:2px solid var(--syn-edge);background:var(--syn-accent);color:var(--syn-bg);font:inherit;font-weight:800;cursor:grab;touch-action:none;box-shadow:0 3px 0 var(--syn-edge);user-select:none}
.syn-mass.syn-dragging{position:relative;z-index:2;cursor:grabbing;opacity:.9}
.syn-scene{width:100%;max-height:260px;height:auto}
.syn-valves{display:flex;align-items:center;gap:8px}
.syn-valve{min-width:88px;min-height:44px;padding:0 16px;border-radius:999px;border:2px solid var(--syn-edge);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:800;cursor:pointer;touch-action:none;user-select:none;box-shadow:0 3px 0 var(--syn-edge)}
.syn-valve.syn-open{background:var(--syn-accent);color:var(--syn-bg)}
.syn-titr{display:grid;gap:6px;max-width:300px}
.syn-titr-frame{position:relative}
.syn-titr-frame .syn-scene{max-height:none;display:block}
.syn-eye{position:absolute;left:55.4%;transform:translateY(-50%);min-width:44px;min-height:44px;padding:0 10px;border-radius:999px;border:2px solid var(--syn-edge);background:var(--syn-card);color:var(--syn-fg);font:inherit;font-weight:800;cursor:grab;touch-action:none;user-select:none;box-shadow:0 3px 0 var(--syn-edge)}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
`;
