# Plans with no textbook basis

A Plan lands here when the supplied KSSM textbooks do not state what it teaches. It is kept (not deleted) so the work is not lost, but it is **not** a golden Plan: nothing in `data/plans/*.json` loads from this folder, and it cannot carry a citation.

| Plan | Why it is here | Found |
|---|---|---|
| `biology-f4-cardiac_output.json` | Cardiac output as heart rate times stroke volume. Neither the English nor the Malay Biology Form 4 or Form 5 textbook contains "cardiac output" or "stroke volume" (searched 2026-10-18). Heart rate appears only in a pulse-rate practical and in the fight-or-flight list. | 2026-10-18 |

To bring a Plan back: find the page in an official KSSM book that states it, add the pointer in `data/citations/pointers.json`, and move the file up.
