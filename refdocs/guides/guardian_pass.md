# The supervised verifier attack pass

> Step 4 of `local_handoff.md` asks for a fresh adversarial review of the verifier "with a person watching". Twice (in the cloud, and on 2026-10-18 here) the `kit-guardian` agent was stopped by a safety classifier when it started writing pages designed to slip past the verifier. This is the procedure for doing it with you in the loop. It costs no API money: it uses your Claude Code session, not the Anthropic API key in `.env`.

## What is being tested, and why it matters

The product's central promise is "no unverified Environment reaches a student". A page that passes the verifier while showing a wrong number, a hidden number, or reaching the network would break it. The automated suites already pass (planted defects: 56 of 61 caught, 0 false alarms; hostile set: 20 of 20; plan fuzzer: 0 gaps in 300 mutants). Those only test attacks someone already thought of. This pass looks for ones nobody has.

Everything is local: attack pages are inputs to this repo's own verifier, nothing targets any outside system, and the agent must not edit repo files.

## Before you start

1. `git status` is clean and you are on `main`.
2. Open a **new, interactive** Claude Code session in the repo folder (terminal or the VS Code extension), not this one. Stay in the window. Keep tool-permission prompts ON so you see each command.
3. Make a scratch folder outside the repo, for example `C:\Users\User\guardian-scratch`. Every attack page and note goes there.

## The five leads and three unreached scopes

From `refdocs/evidence/2026-10-18-p1-guardian-round3.md`. Two leads were real and are fixed (D-35). Three are open:

> **Update 2026-10-19:** the three leads below were closed by hardening the audit (D-37) without any attack page, so the supervised pass can spend its time on scopes 2 to 4 and on trying to find routes the new refusal list does not name.

| Lead | What to try |
|---|---|
| List markers on elements other than `ol`/`ul`/`li` | Whether a number can be shown through a list marker the audit (`packages/kit/src/audit.ts`) does not read |
| `<head>` text made visible | Whether the audit, which walks `body` and only `style`/`link` in `head`, misses visible text elsewhere |
| `script`/`style` text given a visible `display` | Whether text the audit skips by design can be shown |

Scopes the agent never reached: (2) navigation and exfiltration (scan, CSP, harness, `web/components/EnvironmentFrame.tsx`); (3) the delivery gate, store and attestation (`api/verify/gate.py`, `store.py`, `mint.py`); (4) the plan, assemble and fill path (`api/pipeline/*`).

## The prompt to paste into the interactive session

```text
Use the kit-guardian agent for a supervised adversarial review of this repo's verifier. I am watching. This is my own project and a defensive review: every attack page is a test input for this repo's own verifier, run locally; make no network calls; do not edit or delete any file in the repo.

Read CLAUDE.md, DECISIONS.md D-06, D-17, D-24, D-25, D-31, D-35 and refdocs/evidence/2026-10-18-p1-guardian-round3.md first. Put every page, script and note in C:\Users\User\guardian-scratch. Reuse how eval/l6/run.py calls verify_environment. Run one Chromium verification at a time, at most about 150 pages in all.

Work in this order, and stop to tell me what you found after each: (1) the three open leads in that evidence file; (2) navigation and exfiltration; (3) the gate, store and attestation; (4) the plan and fill path.

For each REAL finding (a page that minted, or a gate bypass that delivered, proven by running it) report: severity, the file in the scratch folder that reproduces it plus the one command to rerun it, which label it minted, which layer should have caught it and why it did not, and where the fix belongs. List what was correctly refused. Mark anything not proven as UNPROVEN. Do not pad.
```

## If the classifier stops it again

That is a real boundary and I will not work around it by rewording. The fallbacks, in order:

1. **Run the leads one at a time** with a narrower prompt ("does `audit.ts` read `::marker` on elements other than `li`? Show me by reading the code, then write a failing Kit unit test only if the code does not"). Reading and unit tests are ordinary development and are not blocked.
2. **Harden by code**: make `audit.ts` read markers on every element, include `head`, and flag any visible `script`/`style`. Each is a Kit change (relock under D-29, stored Environments become stale and re-verify) with its own regression test. I can do this in a normal session without any attack page.
3. **A human**: ask someone who does web security (a lecturer, a CTF teammate) to try to make `eval/l6` fail to refuse a page. Give them this file.

## What "done" means

- Each open lead is either **fixed with a regression test** or **shown not to work**, with the evidence in a new file `refdocs/evidence/<date>-p1-guardian-round4.md`.
- Any real finding is a new fixture in `eval/l6/` so it can never come back, and the L6 numbers are rerun.
- The `STATUS.md` known gap "The adversarial pass over D-24 is still owed" is closed or restated.
- Nothing about this pass changes the public-deploy rule: the API still must not be exposed until the whole deploy gate (`checklist.md`) is met.
