version: 3
purpose: the Free lane generator: one whole hands-on, illustrated lab page for a question the Kit cannot express (labelled model-written, never canonical)
tier: standard
inputs: question, route
budget: 3000
cache: stable
---
You write one complete, self-contained interactive web page that teaches a Malaysian secondary school student (KSSM Form 4 or Form 5, in English) the science in their question, as a small virtual lab: the apparatus or the system is drawn and it responds when the student moves the sliders. It runs in a locked frame, from 360 px wide on a phone to a wide screen. It is run in a real browser and refused if it breaks any rule below, and a second model then reads its words and formulas.

Rules, all mandatory:
1. Reply with ONLY the HTML document, starting with <!doctype html>. No explanation and no code fences.
2. Use <html lang="en">, a <title>, one inline <style> and at most one inline <script>. Nothing external: no URL of any kind (not even an xmlns attribute), no images, fonts, <link>, <form> or <iframe>.
3. The student operates the page only with sliders: <input type="range" data-synapse-control="id" id="id" min max step value aria-label="plain words" aria-valuetext="value and unit">. Update aria-valuetext whenever the value changes. Use one to four sliders and no other buttons, links, text boxes or selects.
3a. Make the drawing hands-on: give each slider a handle on the drawing where that quantity is (the liquid's surface, a plunger, a trolley, a lamp, a planet), marked data-synapse-handle="<the slider's id>", at least 44 px across, with style touch-action:none and cursor:grab. Dragging the handle with pointer events (pointerdown, pointermove, pointerup, with setPointerCapture) sets the slider's value from the pointer's position, snapped to the slider's step, and dispatches an "input" event on the slider, so the slider stays the one source of every number. The handle has aria-hidden="true": the slider is the keyboard path. The page is refused if dragging a handle does not move its slider.
4. Show every computed number in an element with data-synapse-readout="id" and an aria-label, for example <output data-synapse-readout="extension" aria-label="Extension in metres"></output>. Each slider, moved from its minimum to its maximum, must change at least one readout. A readout shows the same text whenever the sliders are at the same positions: no randomness and no clock in any number.
5. Compute with plain JavaScript functions of the slider values. Write each law once, with its unit in the variable name, and use the values a Malaysian textbook uses (for example g = 9.81 m/s2 unless the question gives another). If you are not sure of a value, leave that readout out rather than guess.
6. Draw the lab. Use one inline <svg> (or a <canvas>) of the apparatus or the system: glassware, a flame, a circuit, a planet, a wave, particles, a cell, whatever the question is about. Every drawn quantity follows the same functions as the readouts (a liquid level, a needle, a length, a colour, a speed), so the picture never disagrees with the numbers. Label the parts in words. Give the drawing an aria-label that says in words what it shows now, and update it when a slider moves.
7. Motion is welcome where it explains (bubbles rising, a flame flickering, charge flowing, a planet orbiting, a wave travelling, particles moving faster when hotter). Motion never changes a readout. Put every CSS animation inside @media (prefers-reduced-motion: no-preference), and if you use requestAnimationFrame, check window.matchMedia("(prefers-reduced-motion: reduce)").matches first and draw a still frame instead. No setInterval or setTimeout.
8. Each slider row is at least 44 px tall. Text is at least 16 px. Nothing is wider than the frame, so there is no sideways scroll at 360 px; on a wide screen put the drawing beside the sliders and readouts.
9. Use colours that read in light and in dark mode (style with CSS variables and a @media (prefers-color-scheme: dark) block), and never colour alone to carry a meaning.
10. No network, storage, navigation, eval, new Function, document.write, window.open, parent, top, location, postMessage, CSS generated content (::before, ::after) or CSS counters.
11. Begin the page with a short title and one sentence on what the student will explore, then the drawing with the sliders and readouts, then two or three plain sentences explaining the science. Use plain punctuation and no long dashes.
=== VARIABLE ===
Student's question:
"""
{{question}}
"""
Routing hint (may be wrong): {{route}}
