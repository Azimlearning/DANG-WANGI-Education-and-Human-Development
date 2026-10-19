# Verifier review, round 3 (2026-10-18): what ran, what was stopped, what is open

> Hand-written. The handoff (Step 4) asked for a fresh adversarial pass over D-24 and the whole verifier "with a person watching".

## What ran without any attack page

| Check | Result |
|---|---|
| `eval/l6/run.py` (61 planted defects, 12 neutral controls) | 56 refused, 0 false positives, no surprise misses; the 5 known misses are unchanged. One timer-driven defect is attributed to L1 or L2 depending on timing (see the note now in the report) |
| `eval/hostile/run.py` | 20 of 20 blocked |
| `eval/plans/fuzz.py`, seeds 10 to 19 (10 new seeds, 30 mutants each) | 142 minted of 300, 0 parity gaps |
| `eval/environments/build.py` | 17 of 17 verified and delivered, before and after the two fixes below |

## The agent run was stopped again

The `kit-guardian` agent was launched with a scoped, local-only brief. A safety classifier stopped it after it had read the trust path and written a runner, before it built or ran any attack page, as happened in the cloud. It was not re-launched with different wording to get past the classifier. Scopes 2 to 4 of its brief (navigation and exfiltration, the delivery gate and store, the plan and fill path) were not reviewed at all. **The adversarial pass is therefore still owed, and the handoff's condition ("with a person watching") has not been met.**

## What its code reading suggested

| # | Lead | Status |
|---|---|---|
| 1 | A conversion's starting unit is never compared with its source's unit | **Real, fixed (D-35).** Proved with hand-built chains: `convert(<model output in m>, "mm", "m")` raised no problem before; the old test blessed a newtons control converted "from mm" |
| 5 | `.99 m` and `5e1` are not read as numbers in sentences | **Real, fixed (D-35).** `.99` produced no match; `5e1` produced 5 |
| 2 | `::marker` content is examined only on `ol`, `ul`, `li` (`audit.ts`); another element styled `display: list-item` with a string `list-style-type` might show a number with no text node | UNPROVEN. Needs a page to test |
| 3 | The audit walks `body` and only `style` and `link` in `head`; text in `<head>` (a `<title>`) made visible by CSS might escape it | UNPROVEN |
| 4 | Text inside `script` and `style` is skipped by design; given a visible `display` it might show a number | UNPROVEN |

**Update 2026-10-19:** leads 2 to 4 were closed by hardening the audit (D-37) without building any attack page: marker routes in stylesheets, inline styles and on any element, and non-visual elements made visible, are now all refused. They were never shown to be exploitable, so they are "hardened", not "fixed". The supervised pass is still owed for the three unreached scopes and for anything the new list does not name.

Leads 2 to 4 were for a run with a person watching, starting with the three above, then the three scopes not reached.
