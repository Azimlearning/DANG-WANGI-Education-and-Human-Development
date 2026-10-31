version: 1
purpose: the last step when no fuller lab passed its checks (W20, D-80): one small, hands-on lab page for the student's question that passes every check the first time (labelled model-written, never canonical)
tier: standard
inputs: question, route
budget: 2400
cache: stable
---
You write one small, complete, self-contained interactive web page: a simple virtual lab for a Malaysian secondary school student (KSSM Form 4 or Form 5, in English) about their question. A fuller lab could not be made, so this one must be simple, correct and certain to work. Small and right beats rich and broken. It runs in a locked frame from 360 px wide, is run in a real browser and refused if it breaks any rule below, and a second model then reads its words and formulas.

Choose the one relationship at the heart of the question (for example how the period of a pendulum depends on its length, how the rate depends on temperature, how the angle of refraction depends on the angle of incidence) and let the student change the cause and see the effect. If the question is not about science, choose the science closest to it that a student could explore, and say so in one sentence.

Rules, all mandatory:
1. Reply with ONLY the HTML document, starting with <!doctype html>. No explanation and no code fences.
2. Use <html lang="en">, a <title>, one inline <style> and one inline <script>. Nothing external: no URL of any kind, no images, fonts, <link>, <form> or <iframe>.
2a. The page is scanned as text, comments included, and refused if any of these appear anywhere: http:// or https:// (so no xmlns attribute, and no SVG namespace written out: make SVG shapes by writing them in the HTML, or in the script take the namespace from an <svg> already in the page, var NS = svgElement.namespaceURI), fetch(, XMLHttpRequest, WebSocket, localStorage, sessionStorage, indexedDB, eval(, Function(, a function named open, postMessage, parent, top, location, document.write, import, export, setTimeout or setInterval.
3. One or two sliders, no more: <input type="range" data-synapse-control="id" id="id" min max step value aria-label="plain words" aria-valuetext="value and unit">. Update aria-valuetext whenever the value changes. No other buttons, links, text boxes or selects.
4. One handle on the drawing for each slider, marked data-synapse-handle="<the slider's id>", at least 44 px across, aria-hidden="true", style touch-action:none and cursor:grab. On pointerdown call setPointerCapture; on pointermove, while held, set the slider from the pointer's position along the handle's track (left to right across the drawing, or bottom to top), snapped to the step, then dispatch new Event("input", {bubbles: true}) on the slider; on pointerup let go. The page is refused if dragging a handle does not move its slider.
5. Two or three readouts, each <output data-synapse-readout="id" aria-label="what it is, with the unit">. Each slider, moved from its minimum to its maximum, must change at least one readout. No randomness and no clock in any number.
6. One plain function per law, with the unit in the variable names and textbook values (g = 9.81 m/s2 unless the question gives another). If you are not sure of a value, leave that readout out rather than guess.
7. One inline <svg> with an aria-label describing what it shows, updated when a slider moves: the apparatus or the system, simply drawn and labelled in words, with one drawn quantity (a length, a level, a size, an angle, a colour) that follows the same function as a readout. Put CSS transitions on that quantity inside @media (prefers-reduced-motion: no-preference) so it glides. No requestAnimationFrame.
8. Layout: a title, one "Try this" line saying what to drag, the drawing, the readouts, a small "Fine control" panel with the sliders (each row at least 44 px tall), then two or three plain sentences explaining the science. Text at least 16 px; nothing wider than the frame. Use CSS variables with a @media (prefers-color-scheme: dark) block, and never colour alone to carry a meaning. Plain punctuation, no long dashes. No ::before, ::after or CSS counters.
9. Keep it short: the script under 6,000 characters and the whole page under 12,000.
=== VARIABLE ===
Student's question:
"""
{{question}}
"""
Routing hint (may be wrong): {{route}}
