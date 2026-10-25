# Execution: W5c, the exam mirror

> Plan: `refdocs/plans/2026-10-25-w5c-exam-mirror.md`. Keep this file true to what happened (CLAUDE.md rule 4). No paid call is made by anything here.

| # | Task | Files | Verify | Status |
|---|---|---|---|---|
| 1 | `data/exam_items.json` and its loader | `data/exam_items.json`, `api/models/exam.py`, `test_exam.py` | planted-fault tests | Done |
| 2 | The `exam` event, codegen, emit after the topic is known | `packages/schema/src/events.ts`, `api/pipeline/run.py`, `api/pipeline/test_exam.py` | tests incl. spy provider | Done |
| 3 | The marker | `web/lib/exam.ts`, `exam.test.ts` | web tests | Done |
| 4 | The card and the stream plumbing | `web/lib/{stream,turns}.ts`, `web/components/ExamCard.tsx`, `MessageList.tsx` | web tests | Done |
| 5 | Smoke at 360 px | `eval/smoke/web_smoke.py` | smoke | Done |
