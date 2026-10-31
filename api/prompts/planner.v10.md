version: 10
purpose: turn a routed question into a validated Plan (data, no code), with real apparatus on the bench that the student handles, checked against the four demo labs, and say honestly how well the Kit fits
tier: standard
inputs: schema, pattern_pack, apparatus_pack, kit_pack, exemplar, question, route, issues
static_inputs: schema, pattern_pack, apparatus_pack
budget: 4400
cache: stable
schema: schemas/plan.schema.json
---
Task: write the Plan for one interactive Environment that answers the student's question.

A Plan is data. It names sliders with ranges, science models with parameters, readouts, the apparatus on the bench, and the short words around them. Code is assembled from it by Synapse.

How to plan:
- Pick the one model in the Kit that matches the question. Set its parameters to values a textbook would use, inside the model's domain.
- A model line in the Kit list ends "in a Plan:" with the exact id for "model", its input names and its param names. Copy the id exactly. Each input is bound to a slider or constant; each param is a fixed number you set. Never invent an id: if no listed model fits, pick the closest listed one.
- Sliders: one per quantity the student should vary, with a range that makes the pattern easy to see and stays inside the model's domain. Give each a starting value inside its range and a grid (the number of equal intervals to test).
- Bind each model input to a slider or constant of the same unit, or to a model listed EARLIER in "models", whose output then feeds it (same unit). Chains show cause and effect: gravity feeds weight, and weight feeds a spring balance (mechanics.hookes load). At most three models.
- Copy units exactly as the Kit list writes them. Degrees Celsius is "°C", never "C" (C is the coulomb).
- Readouts: show what the model returns, in its unit (or a conversion the Kit knows).
- The goal is one sentence of at most 240 characters.
- Words: a short study note (what the law says), at most a few sentences, and steps if the pattern needs them. Only use numbers that are slider values, grid positions, constants or model parameters.
- Keep it small. Fewer parts that work beat many parts.
- Planets: when the question compares planets or the Solar System, add a control with surface "planets" (min 1, max 8, grid 7, unit "planet", value 3 for Earth) and feed physics.planet_gravity from it; physics.weight turns that gravity into a weight. A graph whose x is the planets control draws one bar per planet.

Hands, not sliders: the student should operate the drawing, not a row of sliders.
- Prefer a control surface whenever one fits: "masses" for loads added in equal steps, "planets" for which planet, "valve" for liquid run in from a burette, "dial" for a knob or a timer.
- A graph's point can always be dragged, and so can a bench channel marked [drag] that is bound to the slider itself. So put the quantity the student varies on the x axis of a graph, or on a [drag] channel.

How well the Kit fits ("fit" and "missing"):
- "fit": "full" when a listed model computes the quantity the question is really about.
- "fit": "partial", with "missing" saying in one sentence what the Kit cannot show, when no listed model computes that quantity and your Plan can only show something near it. That question then gets a page written for it, and your Plan is the fallback. Never use "partial" to avoid work: if a listed model computes it, the fit is "full".

The bench (the "apparatus" list): put the equipment a student would see in this experiment on the bench, so the page is a lab and not only a graph.
- Use 1 to 4 parts from the catalogue below. Give each a short label in the student's words ("Water", "Tube A", "Ammeter").
- Bind every required channel, and only the channels the part has, to the id of a slider or a model instance. Never to a constant: a part must move when something changes.
- Every channel in the catalogue is a fraction channel unless it is marked (ph) or (angle); a thermometer's temperature, a leaf's light and a gauge's value are fraction channels too.
- A fraction channel needs "full": a round number a little above the largest value that source reaches over the sliders' ranges (the value drawn as a full beaker, the biggest flame). It must be at least that largest value and at most four times it.
- A fraction channel's source must stay at zero or above over the sliders' ranges. A net rate, a change or a difference that can go below zero cannot drive a part: bind the channel to a quantity that stays positive (the light intensity, the gross amount) or leave an optional channel out.
- An angle channel takes a value in deg from 0 to 60, a pH channel a value in pH from 0 to 14; neither takes a "full". A pH channel needs a model output in pH: if no model in the Plan gives a pH, do not use the indicator.
- Bind each part to what it really shows: a beaker's level to a volume or an amount of liquid, a thermometer to a temperature, a burner to the heat supplied, a gauge to a reading, a circuit to the current. Do not bind a picture to an unrelated quantity just to make it move.
- Combine parts to show the set-up: a burner under a beaker with a thermometer; a circuit with a bulb; a gas syringe with a pressure gauge; two test tubes for a control.

Make the bench hands-on, the way a student works at a real bench:
- A channel marked [drag] that is bound directly to a slider gets a handle the student drags on the drawing (pour to a level, push the plunger, move the trolley, tilt the ramp, lengthen the pendulum). So when the student varies something they would handle, bind that part's [drag] channel to the slider itself, not to a model's output.
- A part may take a "drop": items the student drags onto it, each one step of a slider. Use it when the experiment adds things in equal portions (spoons of solute into water, slotted masses onto a trolley, drops of acid into a flask, cells into a circuit). "source" is the id of a plain slider with a grid of 2 to 8 (one step per item) that starts on a step; "item" names one portion in the student's words ("Spoon of salt"). The part must show the result: bind one of its channels to that slider or to a model it feeds.

Before you reply, check the Plan against our four demo labs (masses dropped on a spring's hanger, a burette's stopcock held open, yeast and limewater with rising bubbles, Newton's cannon with a draggable launch arrow). A Plan that fails one of these is a worse lab:
1. Something real is drawn: a bench part or a scene that shows the set-up, not only a graph.
2. Every slider has a place on the drawing to work it: a control surface, a "drop", a [drag] channel bound to it, or the x axis of a graph. A slider with none of these is only a bar.
3. Something moves when each slider moves: bind a part's channel to the model output the slider drives, so the picture answers the student's hand.
4. The first step says what to drag or drop ("Drop a mass on the hanger", "Drag the point on the graph to the right"), never "move the slider".

Apparatus catalogue (part: channels, "?" means optional | use when):
{{apparatus_pack}}

Pattern guidance:
{{pattern_pack}}

Schema (reply with JSON that matches it):
{{schema}}

=== VARIABLE ===
Components available (use only these):
{{kit_pack}}

Nearest worked example (for shape only; do not copy its science):
{{exemplar}}

Routing for this question: {{route}}

Student's question:
"""
{{question}}
"""

{{issues}}
