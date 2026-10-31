# Prompt test log (manual testing)

> Internal. One row per prompt tried at http://localhost:3000. Fill the expected columns before you press Ask, the actual ones after. Newest rows at the bottom; keep the IDs.

## How to fill a row

- **Expected (lane, label)**: Library (a stored lab, instant, free), Simple (the fuller lab failed its checks, so a small lab was written for the question; the build log says "a simpler lab is being written", W20), Compose (built from the Kit, about $0.03 to $0.08), Free (a page written whole by a model, estimated $0.10 to $0.20, unmeasured), or Text only.
- **Actual (lane, label)**: read the two badges on the lab frame. Label: Kit verified or Model checked. Lane: From the library, Built for your question (Compose) or Written whole by a model (Free). Open **See how it's built** to see which lane led and why.
- **What the lab showed**: one line. Does it answer what was asked? Can you drag something on it?
- **Cost (USD)**: paid spend for that question if known (library rows are 0). Exact figures: `data/ledger.db`, newest rows.
- **Result**: `PASS` (answers the question and works), `PARTIAL` (a lab came but answers something near it, or a drag or number looked wrong), `FAIL` (no lab, or broken), `FIXED-RETEST` (failed, fix in, not yet retried), `NOT RUN`.
- New problem? Add it to **Known issues** with the row ID.

## Log

| ID | Date | Prompt | Expected (lane, label) | Actual (lane, label) | What the lab showed | Cost (USD) | Result | Notes |
|---|---|---|---|---|---|---|---|---|
| T01 | 2026-10-29 | How much would I weigh on Jupiter compared with Earth? | Library, Kit verified | Library, Kit verified | Planets bench: 24.79 N/kg on Jupiter, 2 kg weighs 49.6 N; test mass and masses drag | 0 | PASS | K1 |
| T02 | 2026-10-29 | Simulate how the Moon's phases happen as it orbits Earth | Free, Model checked | Library, Kit verified | Newton's cannonball (wrong lab, matched on "orbit" and "Earth") | 0 | FIXED-RETEST | K2 |
| T03 | 2026-10-29 | Same as T02 (second try) | Free, Model checked | Text only | No lab: the router found no Form 4 or 5 topic | 0.006 | FIXED-RETEST | K3 |
| T04 | 2026-10-29 | Same as T02 (third try) | Free, Model checked | Compose, Kit verified | "The Moon's orbit and Earth's pull" (the Kit fallback); the Free page was refused | 0.105 | FIXED-RETEST | K4 |
| T05 | 2026-10-29 | Same as T02 (fourth try) | Free, Model checked | Text only | No lab: the plan's reader refused the Kit plan twice, Free never tried | 0.064 | FIXED-RETEST | K5 |
| T06 | 2026-10-28 | Can you simulate the difference in gravitational strength on each planet in my solar system? | Library, Kit verified | Compose, Kit verified (before W19) | "Gravity pull on a planet": sliders, no planets | 0.071 | FIXED-RETEST | Now remembered for the planets bench |
| T07 | 2026-10-29 | What is Newton's cannonball, and how does a satellite stay in orbit? | Library, Kit verified | Library, Kit verified | Drag the arrow to set the speed, press Launch, the ball flies, traces stay | 0 | PASS | |
| T08 | 2026-10-29 | Why does a spring stretch when I hang a weight on it? | Library, Kit verified | Library, Kit verified | Spring on a stand, masses dropped onto the hanger, ruler pointer | 0 | PASS | |
| T15 | 2026-10-29 | Simulate how the Moon's phases happen as it orbits Earth (fifth try) | Free, Model checked | Text only ("wording could not be confirmed") | The Free page was written about the Moon's phases, but its reader was told the topic was nuclear physics (router misfiled it) and refused it as off-topic; two Kit plans refused first | 0.127 | FIXED-RETEST | K12, K13 |
| T09 | 2026-10-29 | How does the angle of a ramp change how fast a ball rolls down it? | Free or Compose | Text only ("used up the steps") | No lab: plan 1 refused by the reader over a non-issue, plan 2 not valid JSON, the Free page cut off at 6000 tokens | 0.14 | FIXED-RETEST | K8, K9, K10 |
| T10 | | Show how a rocket's acceleration changes as it burns its fuel | Free, Model checked | | | | NOT RUN | |
| T11 | 2026-10-29 | Simulate how particles diffuse faster when the temperature is higher | Free, Model checked | Text only | No lab: two plans refused for a topic mismatch (PLAN-016), the Free page refused by the scan; the explanation said it could not output JSON | 0.124 | FIXED-RETEST | K6, K7, K11 |
| T12 | | Why do I weigh less on the Moon than on Earth? | Free or Compose | | | | NOT RUN | |
| T13 | | How does temperature affect the rate of a reaction? | Compose, Kit verified | | | | NOT RUN | |
| T14 | | What is the pH of a strong acid compared with a weak acid? | Compose or Free | | | | NOT RUN | |
| T16 | | How does a lens form an image when I move the object closer? | Compose or Free (W20: drag the object or a graph point) | | | | NOT RUN | Check: can you drag something on the drawing? |
| T17 | | Why does ice melt faster in salt water than in fresh water? | Free (W20: drop salt into a beaker) | | | | NOT RUN | Check: a drop target, things move |
| T18 | | How does the length of a pendulum change its period? | Compose or Free | | | | NOT RUN | Check: drag the bob or the string length |
| T19 | | Why is the sky blue? | Free, or Simple | | | | NOT RUN | Every question must end with a lab (W20) |
| T21 | | What is the capital city of France? | Simple (closest science, said so on the page) | | | | NOT RUN | Not a science question: still a lab |
| T20 | | How do I revise Hooke's law? | Library, Kit verified | | | | NOT RUN | Was planned and paid for before W20 ("revise" is now an asking word) |
| T22 | | simple quantum phy experiment | Free (partial fit), a quantum lab | | | | NOT RUN | Was a Boyle's law syringe; retry after a browser refusal is new |
| T23 | | Show me how the photoelectric effect works | Free | | | | NOT RUN | Drag the light's frequency; no electrons below the threshold |
| T24 | | Why does a ball thrown sideways still hit the ground at the same time as one dropped? | Compose or Free | | | | NOT RUN | Projectile motion; drag the launch speed |
| T25 | | How does a pendulum's length change its period? | Compose (pendulum part) | | | | NOT RUN | Drag the bob or the string |
| T26 | | Make me an experiment on momentum when two trolleys collide | Free (partial fit) | | | | NOT RUN | Was a Newton's second law lab; drop or drag a trolley |
| T27 | | How does adding more resistors in series change the current? | Library or Compose | | | | NOT RUN | Circuit with glowing bulb |
| T28 | | Why does salt dissolve faster in hot water? | Free or Compose | | | | NOT RUN | Drop salt into a beaker |
| T29 | | Compare how fast a feather and a hammer fall on the Moon | Free | | | | NOT RUN | Outside the syllabus; both land together |
| T30 | | How does a heat pump or fridge move heat? | Free | | | | NOT RUN | Outside the syllabus |
| T31 | | What happens to the volume of a balloon when I heat it? | Compose | | | | NOT RUN | Charles' law; drag a burner or thermometer |
| T32 | | Simulate natural selection in a population of moths | Free | | | | NOT RUN | Biology; drag the tree colour |
| T33 | | How does the pH change as I add alkali to an acid? | Library (titration) or Compose | | | | NOT RUN | Hold the stopcock; swirl the flask |
| T34 | | Why do we see different phases of the Moon? | Free | | | | NOT RUN | Old failure K2 to K13 |
| T35 | | explain DNA replication with a simulation | Free | | | | NOT RUN | Biology outside a Kit model |
| T36 | | What is the capital city of France? | Simple (closest science, said so) | | | | NOT RUN | Non-science: must still end in a lab |
| T37 | | Why does yeast make limewater go milky? | Library, Kit verified | | | | NOT RUN | Drag spoons of glucose into the beaker |

## Known issues

| ID | Found in | Issue | Status |
|---|---|---|---|
| K1 | T01 | Planet names crowd each other at wide widths; the bar chart's "Planet" title overlaps the slanted labels | Open |
| K2 | T02 | The library served a lab that shared two words with the question but did not answer it | Fixed 2026-10-29: library serves only when the lab's Plan uses every content word; known questions remembered in `data/library_questions.json` |
| K3 | T03 | A science question outside the Form 4 and 5 topics stopped at text only | Fixed 2026-10-29: a science domain with no topic goes to the Free lane |
| K4 | T04 | Both second readers were cut off at 300 and 400 output tokens, so every Free page was refused as unread | Fixed 2026-10-29: limits 900 and 1500, reader prompts v3 and v2 cap the reply at five issues |
| K5 | T05 | A Kit plan refused twice by its reader went to text only instead of the Free lane | Fixed 2026-10-29: falls through to the Free lane unless `LANE_PREFERENCE=kit` |
| K6 | T11 | The explanation answered "simulate" questions with "I can't output the JSON object": it inherited the planner's JSON contract from the core prompt | Fixed 2026-10-29: explainer v2 has its own prose-only prompt |
| K7 | T11 | Two paid plans refused only because the router filed the question under another topic (PLAN-016) | Fixed 2026-10-29: the Plan takes its models' shared topic, checked again, no second plan paid for |
| K8 | T09 | The plan reader listed a point it found correct as a problem, refusing a good plan | Fixed 2026-10-29: reader prompts v4 list only real problems |
| K9 | T09 | The Free page ran past its 6000-token limit and was cut off, then reported as "used up the steps" | Fixed 2026-10-29: limit 9000, free v5 asks for a compact page, the reader takes a 16,000-character script, a cut-off is reported as a page that could not be written |
| K10 | T09 | The second plan reply was not valid JSON | Open: watch for it; one plan retry already covers it |
| K11 | T11 | A Free page refused by the scan was not retried; the trace did not say which API | Fixed 2026-10-29: one retry with the checker's exact reason; the trace records it; free v5 spells out the scanner's rules |
| K12 | T15 | The Free page's reader judged it against the routed topic, which the router had got wrong (Moon phases filed as nuclear physics), and refused a correct page | Fixed 2026-10-29: the reader judges the page on its own title, gets textbook notes only when the local router was sure, and reader v4 never refuses for topic or syllabus alone |
| K13 | T15 | A second Kit plan was paid for after the reader refused a plan the planner had already called a partial fit | Fixed 2026-10-29: a refused partial-fit plan goes straight to the Free lane |
| K14 | Spring quick-start during rebuild | The plan reader listed a point it had just called correct ("no error there") and refused a good plan | Fixed 2026-10-29: such self-cleared issues are dropped, and kept in the trace |
| K15 | Library rebuild | The verifier dragged a graph handle with the other controls left at their ends (0 V), so a working Ohm lab was refused | Fixed 2026-10-29: other controls go to their defaults first |
