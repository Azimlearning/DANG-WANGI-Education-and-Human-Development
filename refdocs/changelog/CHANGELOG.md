# Synapse v4: Changelog

> Mandatory session log. Add an entry after **every** session where code changed, a decision was made, or a plan was modified. Newest first. Even a one-line fix gets a one-line entry.

Entry format:
```
### YYYY-MM-DD: [short summary of session goal]
- **Changed:** what files/components were touched and why
- **Decided:** any architectural or design decisions and the reasoning
- **Deviations:** anything that differed from the plan, and why
- **Verified:** what was actually run, and the result (not "should work")
- **Known issues / next steps:** what was left open
```

Those five lines are the floor, not the ceiling. Add these when the session earns them:
- **Reported:** the symptom in the user's own words, before you knew the cause
- **Diagnosed:** what you found, and how you proved it: the reproduction, not the hypothesis
- **Trade-off:** what this change costs, and who it costs it to
- **Noted, not changed:** something you found and deliberately left alone

Rules that make this file worth keeping:
- **"Verified" means a command was run.** Name it and give the result. If nothing was run, write "nothing verified this session".
- **Deviations are the most valuable line.** A plan that changed silently is a plan nobody will trust next time.
- **Write what you learned, not what you touched.**
- Don't rewrite history. Corrections go in a new entry that references the old one.

---

## [Unreleased]

### 2026-10-16: Project scaffolded
- **Changed:** Created the project doc system: `refdocs/` (PRD, STATUS, sources, guides/, changelog/DECISIONS, plans/, execution/), `CLAUDE.md`, `README.md`, `.gitignore`, `.env.example`, `.claude/` (settings, three agents, three commands, preflight, secret-guard hook). Wrote the founding brainstorm `refdocs/brainstorm-2026-10-16.md` with its Amendment A1. No application code yet.
- **Decided:** ADRs D-01 to D-14. In particular: "environment" is the artifact term (D-01); raw HTML/JS stays primary in three lanes (D-02); a Kit of hundreds of micro-components is an allowed building block (D-03); the Mark 3 pipeline is prompt packs plus the Kit plus accelerators (D-04); Python API + Next.js + schema + JS Kit (D-05, the agent's call as delegated); fakes by default and the owner confirms paid runs (D-08); no auth and no rate limit, so no public exposure until a deploy gate (D-11).
- **Deviations:** The founding brainstorm first recommended a data-first design with raw HTML only at authoring time. The owner rejected that in the interview; the brainstorm carries an amendment that supersedes the conflicting sections, and the PRD reflects the owner's choice. No parity doc and no file-structure doc were written (see STATUS Known gaps).
- **Verified:** Toolchain versions only (`uv --version`, `node --version`, `pnpm --version`, `python --version`, `git --version`, `df -h`); see STATUS verification ledger. Nothing else to verify: no code exists.
- **Known issues / next steps:** Eighteen `ASSUMED:` items are open (PRD section 8), the load-bearing ones being the oracle (A-5), the Kit API and size (A-2), isolation (A-10), exposure reading (A-11) and corpus legality (A-8). Next session starts from `refdocs/plans/2026-10-16-p0-walking-skeleton-census.md`.
