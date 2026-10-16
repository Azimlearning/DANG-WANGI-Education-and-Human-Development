"""P0 coverage census: 53 KSSM topics annotated against the Kit's micro-component kinds.

    uv run python eval/census/census.py --check          # validate the table; exit 0 or 1
    uv run python eval/census/census.py --report         # print counts and the ranking
    uv run python eval/census/census.py --write-report   # regenerate refdocs/evidence/2026-10-16-p0-census.md

WHAT THIS IS. A judgement exercise over a taxonomy, written by one reader (a model) from each topic's name and short phrasing hint.
It is NOT a measurement: no textbook was opened, no Environment was generated, no Kit component exists beyond Kit v0. Every cell is an
ESTIMATE with a confidence. Its only job is to order P1 and P4 (which science micro-models to build first) and to inform the choice
of a first vertical (D-09), which the owner decides. None of its numbers is a coverage claim.

THE CRITERIA ARE WRITTEN FIRST, below, before any topic is annotated. A row is judged only against these definitions.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOPICS_FILE = REPO / "data" / "kssm_topics.json"
REPORT_FILE = REPO / "refdocs" / "evidence" / "2026-10-16-p0-census.md"

# ── 1. COLUMN DEFINITIONS AND CRITERIA (fixed before annotation) ─────────────────────────────────────────────────────────

COLUMNS: dict[str, tuple[str, dict[str, str]]] = {
    "pattern": (
        "The shape of the best learning Environment for the topic, judged from what a KSSM student must understand or do.",
        {
            "simulation": "A system whose behaviour changes as parameters change, and the student explores the relationship.",
            "virtual_experiment": "A practical the student would do in a lab, run virtually with controls and measured results.",
            "explorable_diagram": "A labelled or structured picture the student manipulates or interrogates; no dynamics beyond a state change.",
            "process": "An ordered sequence of stages or a mechanism the student steps through.",
            "data_viz": "Data or curves the student reads, compares or plots; the point is interpreting a graph or table.",
            "exam_practice": "Worked calculations or question practice with checked answers.",
            "text_only": "Little that is interactive and checkable; a study note is the honest answer.",
        },
    ),
    "model_kind": (
        "The kind of declared science behind the numbers or states shown. This decides whether a science micro-model can carry truth.",
        {
            "closed_form": "Outputs follow directly from inputs by a formula (Hooke's law, Ohm's law, pH, Snell's law). Easiest to reference.",
            "stepped": "State evolves step by step or over time (kinematics with a time step, population change, feedback loops).",
            "combinatorial": "Outcomes are enumerated from discrete choices (Punnett squares, balancing equations, lookup tables of results).",
            "stochastic": "Outcomes involve random sampling (decay events, particle collisions, variation). Needs a seeded model and a stated tolerance.",
            "process": "Ordered stages with no numeric model; truth is the correct order and description.",
            "qualitative": "Relationships and facts without numbers; truth is classification or description.",
            "none": "No model needed.",
        },
    ),
    "kit_kinds_needed": (
        "The Kit micro-component KINDS the best Environment would need (PRD 3.4). A subset of the five values; `ui` means any control or readout.",
        {
            "ui": "Sliders, readouts, steppers, study-note cards.",
            "scene": "Drawn pictures: axes, apparatus, diagrams, molecules, waves.",
            "interaction": "Drag, drop, pointer gestures, clicking parts of a diagram.",
            "science": "At least one audited science micro-model (cited, referenced, tested) carries a number or outcome.",
            "pedagogy": "Predict cards, concept checks, misconception probes, worked solutions.",
        },
    ),
    "expected_lane": (
        "The lane the best Environment would most likely survive verification in. A prediction, not a result (D-02).",
        {
            "instantiate": "A stored or template Environment would do; little needs generating per question.",
            "compose": "A model composes it from audited Kit parts; every shown number can come from a science micro-model.",
            "free": "The Kit cannot be expected to express it (a custom scene or behaviour), so it would be written whole and labelled model-checked.",
        },
    ),
    "confidence": (
        "How sure the ANNOTATOR is of this row's judgement, from the topic name and hint alone. Not a measure of Kit coverage.",
        {
            "high": "The topic's content clearly implies this; another reader would very likely agree.",
            "medium": "Plausible and defensible, but a reasonable reader could choose differently.",
            "low": "A guess. The topic's content could support more than one answer, or the Kit cannot be judged from the name.",
        },
    ),
}

# `candidate_models` is a sixth column the ordering task needs: the science micro-models a topic could be served by, as proposed ids
# `<domain>.<name>`. They are NAMES ONLY, proposals for P1 and P4; none exists and none has been checked against a textbook.
CANDIDATE_MODELS_DEFINITION = (
    "Proposed science micro-model ids that could carry the topic's truth. A topic with an empty list has nothing numeric or "
    "enumerable for a science micro-model to own. Ids are proposals; none exists beyond `mechanics.hookes` (Kit v0)."
)

KIT_KINDS = tuple(COLUMNS["kit_kinds_needed"][1])
PATTERNS = tuple(COLUMNS["pattern"][1])
MODEL_KINDS = tuple(COLUMNS["model_kind"][1])
LANES = tuple(COLUMNS["expected_lane"][1])
CONFIDENCES = tuple(COLUMNS["confidence"][1])

# ── 2. ANNOTATIONS ───────────────────────────────────────────────────────────────────────────────────────────────────────
# slug: (pattern, model_kind, kit_kinds, candidate_models, expected_lane, confidence, one-line rationale)
# Every row is an estimate made from the topic name and its hint. Rationales say what drove the choice, in one line.

U, S, N, SC, P = "ui", "scene", "interaction", "science", "pedagogy"

ROWS: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], str, str, str]] = {
    # ── Biology, Form 4 ──
    "cell_structure_function": (
        "explorable_diagram",
        "qualitative",
        (U, S, N, P),
        (),
        "compose",
        "medium",
        "Label and compare organelles in plant and animal cells; classification and description, so no number for a science model to own.",
    ),
    "chemical_composition_of_cell": (
        "virtual_experiment",
        "combinatorial",
        (U, S, SC, P),
        ("bio.food_tests",),
        "compose",
        "medium",
        "Food tests are a practical whose results are a reagent by nutrient lookup; the rest of the topic is classification.",
    ),
    "movement_of_substances": (
        "simulation",
        "stepped",
        (U, S, N, SC, P),
        ("bio.osmosis_flux", "bio.diffusion"),
        "compose",
        "high",
        "Diffusion and osmosis are the classic parameter-and-watch simulations, with a net-flux rule a micro-model can own.",
    ),
    "metabolism_and_enzymes": (
        "data_viz",
        "closed_form",
        (U, S, SC, P),
        ("bio.enzyme_rate_curve",),
        "compose",
        "medium",
        "Enzyme activity against temperature and pH is read as a curve; the syllabus treats it as a shape, so the model is a curve not a law.",
    ),
    "cell_division": (
        "process",
        "process",
        (U, S, N, P),
        (),
        "compose",
        "high",
        "Mitosis and meiosis are ordered stages to step through; chromosome behaviour is description, not calculation.",
    ),
    "respiration": (
        "process",
        "process",
        (U, S, P),
        (),
        "compose",
        "medium",
        "Aerobic against anaerobic pathways and energy yield are stages and a comparison; any numbers are a fixed table, not a model.",
    ),
    "respiratory_system": (
        "process",
        "process",
        (U, S, N, SC, P),
        ("gas.boyle",),
        "compose",
        "medium",
        "The breathing mechanism is a pressure and volume story that Boyle's law can carry, shared with the Physics heat topic.",
    ),
    "digestion": (
        "process",
        "process",
        (U, S, N, P),
        (),
        "instantiate",
        "high",
        "A sequence of organs, enzymes and products to step through; a stored Environment would serve most questions.",
    ),
    "circulatory_system": (
        "explorable_diagram",
        "combinatorial",
        (U, S, N, SC, P),
        ("bio.blood_groups",),
        "compose",
        "medium",
        "Heart and vessels are a diagram; blood-group compatibility is an enumerable table. The topic mixes the two.",
    ),
    "immunity": (
        "process",
        "qualitative",
        (U, S, P),
        (),
        "instantiate",
        "medium",
        "Defence mechanisms and antibody action are described and sequenced; nothing numeric to verify.",
    ),
    "coordination_and_response": (
        "process",
        "qualitative",
        (U, S, N, P),
        (),
        "compose",
        "medium",
        "Reflex arcs and synapses are paths to trace; interaction is clicking along the path, with no number involved.",
    ),
    "homeostasis_and_urinary_system": (
        "simulation",
        "stepped",
        (U, S, SC, P),
        ("bio.feedback_loop",),
        "compose",
        "medium",
        "Negative feedback (glucose, temperature, water balance) is a stepped loop a micro-model can own; the urinary anatomy is a diagram.",
    ),
    "support_and_movement": (
        "explorable_diagram",
        "qualitative",
        (U, S, N, P),
        (),
        "instantiate",
        "medium",
        "Skeleton types, joints and antagonistic muscles are labelled structures; a stored Environment is probably enough.",
    ),
    "reproduction_development_growth": (
        "process",
        "process",
        (U, S, P),
        (),
        "instantiate",
        "medium",
        "Fertilisation and development are staged processes; hormone-level curves could add a data_viz but are not required.",
    ),
    # ── Biology, Form 5 ──
    "plant_tissues_and_growth": (
        "data_viz",
        "closed_form",
        (U, S, SC, P),
        ("bio.growth_curve",),
        "compose",
        "medium",
        "Growth curves are read from a sigmoid shape; the tissue part is a diagram.",
    ),
    "leaf_structure_function": (
        "virtual_experiment",
        "closed_form",
        (U, S, SC, P),
        ("bio.photosynthesis_rate",),
        "compose",
        "medium",
        "Photosynthesis rate against light, with the compensation point, is a classic virtual practical on a curve; transpiration adds a second one.",
    ),
    "nutrition_in_plants": (
        "virtual_experiment",
        "combinatorial",
        (U, S, P),
        (),
        "instantiate",
        "low",
        "Mineral deficiency symptoms are a lookup; whether that is worth a model or only a stored card is unclear from the name.",
    ),
    "transport_in_plants": (
        "simulation",
        "stepped",
        (U, S, N, SC, P),
        ("bio.potometer",),
        "compose",
        "medium",
        "Transpiration pull and potometer readings give a rate to explore; vascular tissue is a diagram.",
    ),
    "response_in_plants": (
        "virtual_experiment",
        "qualitative",
        (U, S, P),
        (),
        "instantiate",
        "medium",
        "Tropisms and auxin are shown as outcomes of set-ups; the results are qualitative.",
    ),
    "sexual_reproduction_in_plants": (
        "explorable_diagram",
        "process",
        (U, S, N, P),
        (),
        "instantiate",
        "high",
        "Flower structure and the steps from pollination to seed are a labelled diagram and a sequence.",
    ),
    "plant_adaptations": (
        "explorable_diagram",
        "qualitative",
        (U, S, N, P),
        (),
        "instantiate",
        "high",
        "Matching structure to habitat is classification; no numbers.",
    ),
    "biodiversity": (
        "explorable_diagram",
        "combinatorial",
        (U, S, N, SC, P),
        ("bio.dichotomous_key",),
        "compose",
        "medium",
        "Classification keys are enumerable decision paths a micro-model can check; naming and microorganisms are facts.",
    ),
    "dynamic_ecosystem": (
        "simulation",
        "stepped",
        (U, S, N, SC, P),
        ("bio.population_growth", "bio.energy_pyramid"),
        "compose",
        "high",
        "Populations over time and the energy lost between trophic levels are stepped or closed-form relationships students explore.",
    ),
    "environmental_sustainability": (
        "text_only",
        "qualitative",
        (U, P),
        (),
        "instantiate",
        "medium",
        "Threats, conservation and green technology are discussion and case material; little that is interactive and checkable.",
    ),
    "inheritance": (
        "simulation",
        "combinatorial",
        (U, S, N, SC, P),
        ("genetics.punnett",),
        "compose",
        "high",
        "Monohybrid and dihybrid crosses are enumerable outcomes with exact ratios, ideal for a micro-model with a hand-written reference.",
    ),
    "variation": (
        "data_viz",
        "stochastic",
        (U, S, SC, P),
        ("bio.variation_histogram",),
        "compose",
        "medium",
        "Continuous against discontinuous variation is read from histograms of sampled data; sampling needs a seed and a tolerance.",
    ),
    "genetic_technology": (
        "process",
        "process",
        (U, S, N, P),
        (),
        "instantiate",
        "medium",
        "Genetic engineering and biotechnology are procedures to step through; a fragment-size table could add a model later.",
    ),
    # ── Chemistry, Form 4 ──
    "introduction_to_chemistry": (
        "explorable_diagram",
        "qualitative",
        (U, S, N, P),
        (),
        "instantiate",
        "medium",
        "Apparatus names, lab safety and the steps of an investigation are recognition tasks, not calculations.",
    ),
    "matter_and_atomic_structure": (
        "explorable_diagram",
        "combinatorial",
        (U, S, N, SC, P),
        ("chem.electron_arrangement", "chem.relative_atomic_mass"),
        "compose",
        "high",
        "Electron arrangements and isotopic averages follow exact rules a micro-model can check.",
    ),
    "chemical_formulae_and_equations": (
        "exam_practice",
        "closed_form",
        (U, N, SC, P),
        ("chem.mole_calc", "chem.balance_equation"),
        "compose",
        "high",
        "Mole calculations and balancing are checkable by rule, with textbook worked examples as a natural independent reference.",
    ),
    "chemical_bonds": (
        "explorable_diagram",
        "combinatorial",
        (U, S, N, SC, P),
        ("chem.bonding_diagram",),
        "compose",
        "medium",
        "Electron transfer and sharing follow the octet rule, but drawing it needs scene parts the Kit does not yet plan.",
    ),
    "periodic_table_of_elements": (
        "data_viz",
        "qualitative",
        (U, S, N, P),
        (),
        "compose",
        "medium",
        "Trends down groups and across periods are patterns read from data; the data itself would have to come from the textbook.",
    ),
    "acids_bases_salts": (
        "virtual_experiment",
        "closed_form",
        (U, S, N, SC, P),
        ("chem.ph_calc", "chem.titration_curve"),
        "compose",
        "high",
        "pH, neutralisation and a titration curve are closed-form with a classic virtual practical on top.",
    ),
    "rate_of_reaction": (
        "simulation",
        "stochastic",
        (U, S, N, SC, P),
        ("chem.rate_curve", "chem.collision_particles"),
        "compose",
        "high",
        "Collision theory is a particle simulation; rate against concentration or temperature is a curve. Both are explored by changing a factor.",
    ),
    "manufactured_substances_in_industry": (
        "process",
        "process",
        (U, S, N, P),
        (),
        "instantiate",
        "medium",
        "Alloys, ceramics and industrial processes are descriptions and flow diagrams.",
    ),
    # ── Chemistry, Form 5 ──
    "electrochemistry_and_redox": (
        "virtual_experiment",
        "combinatorial",
        (U, S, N, SC, P),
        ("chem.electrolysis_products", "chem.cell_emf"),
        "compose",
        "high",
        "Which ion is discharged and the cell voltage follow the electrochemical series; a virtual practical with a lookup and a subtraction.",
    ),
    "carbon_compounds": (
        "explorable_diagram",
        "combinatorial",
        (U, S, N, SC, P),
        ("chem.isomer_naming",),
        "compose",
        "medium",
        "Homologous series, naming and isomers are enumerable; structure drawing is a scene burden.",
    ),
    "thermochemistry": (
        "virtual_experiment",
        "closed_form",
        (U, S, SC, P),
        ("chem.heat_of_reaction",),
        "compose",
        "high",
        "q = mc delta T and energy-level diagrams give checkable numbers from a calorimetry practical.",
    ),
    "polymer": (
        "explorable_diagram",
        "process",
        (U, S, N, P),
        (),
        "instantiate",
        "medium",
        "Addition and condensation polymerisation are described as monomer-to-chain steps; no numeric model needed.",
    ),
    "chemicals_for_consumers": (
        "process",
        "qualitative",
        (U, S, N, P),
        (),
        "compose",
        "low",
        "Micelle formation and cleansing action need a custom animated scene the Kit may not offer, so this could fall to the Free lane.",
    ),
    # ── Physics, Form 4 ──
    "measurement": (
        "virtual_experiment",
        "closed_form",
        (U, S, N, SC, P),
        ("phys.vernier_reading", "phys.micrometer_reading"),
        "compose",
        "medium",
        "Reading a vernier caliper or micrometer is a deterministic rule on a drawn scale; the scene is the hard part.",
    ),
    "kinematics_dynamics_momentum": (
        "simulation",
        "stepped",
        (U, S, N, SC, P),
        ("mechanics.suvat", "mechanics.momentum_collision", "mechanics.newton_second"),
        "compose",
        "high",
        "Linear motion, Newton's laws and momentum are textbook closed-form and stepped simulations with many worked examples.",
    ),
    "circular_motion_and_gravitation": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("mechanics.circular", "gravity.kepler", "gravity.escape_velocity"),
        "compose",
        "high",
        "Centripetal force, Kepler's laws and escape velocity are formulas to explore against an orbit picture.",
    ),
    "heat": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("heat.specific_heat", "heat.latent_heat", "gas.boyle", "gas.charles", "gas.pressure_law"),
        "compose",
        "high",
        "Specific and latent heat and the gas laws are all closed-form with particle or graph pictures.",
    ),
    "waves": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("waves.wave_equation", "waves.interference", "waves.diffraction"),
        "compose",
        "high",
        "v = f lambda is closed-form; interference and diffraction patterns need a wave scene but follow exact geometry.",
    ),
    "light_and_optics": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("optics.snell", "optics.critical_angle", "optics.lens"),
        "compose",
        "high",
        "Refraction, total internal reflection and lens images are closed-form with ray diagrams.",
    ),
    # ── Physics, Form 5 ──
    "force_and_elasticity": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("mechanics.hookes", "mechanics.resultant_force"),
        "compose",
        "high",
        "Hooke's law is the one science micro-model Kit v0 already has; resultant and equilibrium forces add a vector scene.",
    ),
    "forces_and_pressure": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("fluids.pressure_depth", "fluids.hydraulic", "fluids.archimedes"),
        "compose",
        "high",
        "Liquid pressure, Pascal's and Archimedes' principles are closed-form; Bernoulli's principle is harder to picture.",
    ),
    "electricity": (
        "virtual_experiment",
        "closed_form",
        (U, S, N, SC, P),
        ("electricity.ohm", "electricity.series_parallel", "electricity.power"),
        "compose",
        "high",
        "Ohm's law and series and parallel circuits are closed-form; building a circuit needs wire and component scene parts.",
    ),
    "electromagnetism": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("em.transformer", "em.motor_force"),
        "compose",
        "medium",
        "The transformer ratio is closed-form; induction and the force direction rule are three-dimensional and harder to show.",
    ),
    "electronics": (
        "explorable_diagram",
        "closed_form",
        (U, S, N, SC, P),
        ("electronics.rectifier_waveform",),
        "compose",
        "medium",
        "Rectification waveforms follow exactly from a diode rule; transistor behaviour is largely qualitative.",
    ),
    "nuclear_physics": (
        "simulation",
        "stochastic",
        (U, S, SC, P),
        ("nuclear.decay", "nuclear.mass_defect"),
        "compose",
        "high",
        "Radioactive decay is a seeded random process with an exact half-life curve to check it against.",
    ),
    "quantum_physics": (
        "simulation",
        "closed_form",
        (U, S, N, SC, P),
        ("quantum.photoelectric", "quantum.planck"),
        "compose",
        "medium",
        "The photoelectric equation is closed-form; the scene of ejected electrons and the idea of wave-particle duality are harder.",
    ),
}

# ── 3. CHECK ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

EXPECTED_ROWS = 53


def load_topics() -> list[dict]:
    return json.loads(TOPICS_FILE.read_text(encoding="utf-8"))["topics"]


def problems(rows: dict = ROWS, topics: list[dict] | None = None) -> list[str]:
    """Every way the table can be invalid. An empty list means --check passes."""
    topics = topics if topics is not None else load_topics()
    found: list[str] = []
    slugs = [t["slug"] for t in topics]
    if len(slugs) != EXPECTED_ROWS:
        found.append(f"expected {EXPECTED_ROWS} topics in {TOPICS_FILE.name}, found {len(slugs)}")
    if len(set(slugs)) != len(slugs):
        found.append("duplicate slugs in the taxonomy")
    for slug in slugs:
        if slug not in rows:
            found.append(f"{slug}: not annotated")
    for slug in rows:
        if slug not in slugs:
            found.append(f"{slug}: annotated but not in the taxonomy")
    for slug, row in rows.items():
        if len(row) != 7:
            found.append(f"{slug}: expected 7 cells, found {len(row)}")
            continue
        pattern, model_kind, kinds, models, lane, confidence, rationale = row
        if pattern not in PATTERNS:
            found.append(f"{slug}: pattern '{pattern}' is not in the vocabulary")
        if model_kind not in MODEL_KINDS:
            found.append(f"{slug}: model_kind '{model_kind}' is not in the vocabulary")
        bad_kinds = [k for k in kinds if k not in KIT_KINDS]
        if bad_kinds:
            found.append(f"{slug}: kit_kinds_needed has {bad_kinds}, not in the vocabulary")
        if len(set(kinds)) != len(kinds):
            found.append(f"{slug}: kit_kinds_needed repeats a kind")
        if lane not in LANES:
            found.append(f"{slug}: expected_lane '{lane}' is not in the vocabulary")
        if confidence not in CONFIDENCES:
            found.append(f"{slug}: confidence '{confidence}' is not in the vocabulary")
        if "science" in kinds and not models:
            found.append(f"{slug}: needs `science` but names no candidate model")
        if models and "science" not in kinds:
            found.append(f"{slug}: names candidate models but does not list `science`")
        if len(set(models)) != len(models):
            found.append(f"{slug}: candidate_models repeats a model")
        if not (25 <= len(rationale) <= 220) or "\n" in rationale:
            found.append(f"{slug}: the rationale must be one line of 25 to 220 characters ({len(rationale)})")
        if "\u2014" in rationale or "\u2013" in rationale:
            found.append(f"{slug}: the rationale contains an em or en dash")
    return found


# ── 4. COUNTS AND RANKING ────────────────────────────────────────────────────────────────────────────────────────────────


def joined(topics: list[dict], rows: dict = ROWS) -> list[dict]:
    out = []
    for t in topics:
        pattern, model_kind, kinds, models, lane, confidence, rationale = rows[t["slug"]]
        out.append(
            {
                **t,
                "pattern": pattern,
                "model_kind": model_kind,
                "kit_kinds_needed": list(kinds),
                "candidate_models": list(models),
                "expected_lane": lane,
                "confidence": confidence,
                "rationale": rationale,
            }
        )
    return out


def counts(rows: list[dict]) -> dict[str, Counter]:
    by_sf: Counter = Counter(f"{r['subject']} form {r['form']}" for r in rows)
    return {
        "subject and form": by_sf,
        "subject": Counter(r["subject"] for r in rows),
        "pattern": Counter(r["pattern"] for r in rows),
        "model_kind": Counter(r["model_kind"] for r in rows),
        "expected_lane": Counter(r["expected_lane"] for r in rows),
        "confidence": Counter(r["confidence"] for r in rows),
        "kit kind needed (topics)": Counter(k for r in rows for k in r["kit_kinds_needed"]),
    }


def model_ordering(rows: list[dict]) -> list[tuple[str, list[str]]]:
    """Candidate science micro-models by how many topics each would serve, then by name."""
    serves: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        for m in r["candidate_models"]:
            serves[m].append(r["slug"])
    return sorted(serves.items(), key=lambda kv: (-len(kv[1]), kv[0]))


CHECKABLE_KINDS = ("closed_form", "stepped", "combinatorial", "stochastic")


def cluster_scores(rows: list[dict]) -> list[dict]:
    """Rank candidate first verticals (subject, and subject plus form) by estimates. Not a measurement.

    `checkable` = the topic has a numeric or enumerable model AND at least one candidate micro-model AND the lane is not `free`.
    `strong` = checkable AND confidence is high. The ranking is by strong topics, then checkable, then size.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["subject"]].append(r)
        groups[f"{r['subject']} form {r['form']}"].append(r)
    out = []
    for name, rs in groups.items():
        checkable = [
            r
            for r in rs
            if r["model_kind"] in CHECKABLE_KINDS and r["candidate_models"] and r["expected_lane"] != "free"
        ]
        strong = [r for r in checkable if r["confidence"] == "high"]
        models = {m for r in checkable for m in r["candidate_models"]}
        out.append(
            {"name": name, "topics": len(rs), "checkable": len(checkable), "strong": len(strong), "models": len(models)}
        )
    return sorted(out, key=lambda c: (-c["strong"], -c["checkable"], -c["topics"], c["name"]))


# ── 5. REPORT ────────────────────────────────────────────────────────────────────────────────────────────────────────────


def render_report(rows: list[dict]) -> str:
    c = counts(rows)
    lines: list[str] = []
    w = lines.append
    w("# P0 coverage census: 53 KSSM topics against the Kit")
    w("")
    w(
        "> **These are estimates, not measurements.** One reader (a model) annotated each topic from its name and short phrasing hint. No textbook was opened, no Environment was generated, and the Kit has one science micro-model. Every row carries a confidence. The numbers order P1 and P4 and inform the owner's choice of a first vertical (D-09). None is a coverage claim."
    )
    w("")
    w(
        "Generated by `eval/census/census.py --write-report` from `data/kssm_topics.json` and the annotations in that script. Edit the script, not this file."
    )
    w("")
    w(
        "**Owner review: pending.** The owner reviews the table and the ranking, and the review is recorded in the changelog and the STATUS verification ledger. Until then D-09 stays open."
    )
    w("")
    w("## 1. Criteria (written before any row was annotated)")
    w("")
    for name, (definition, vocab) in COLUMNS.items():
        w(f"### `{name}`")
        w("")
        w(definition)
        w("")
        for value, meaning in vocab.items():
            w(f"- `{value}`: {meaning}")
        w("")
    w("### `candidate_models`")
    w("")
    w(CANDIDATE_MODELS_DEFINITION)
    w("")
    w("A row's `rationale` is one line saying what drove the choice. Rows cite the topic name and hint only.")
    w("")
    w("## 2. The table")
    w("")
    w(
        "| # | Subject | Form | Topic | Pattern | Model kind | Kit kinds | Candidate science models | Lane | Conf. | Rationale |"
    )
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        models = ", ".join(f"`{m}`" for m in r["candidate_models"]) or "none"
        w(
            f"| {i} | {r['subject']} | {r['form']} | {r['label']} (`{r['slug']}`) | {r['pattern']} | {r['model_kind']} | {', '.join(r['kit_kinds_needed'])} | {models} | {r['expected_lane']} | {r['confidence']} | {r['rationale']} |"
        )
    w("")
    w("## 3. Counts (all sum to 53)")
    w("")
    for name, counter in c.items():
        if name == "kit kind needed (topics)":
            continue
        w(f"**By {name}** (total {sum(counter.values())})")
        w("")
        w("| Value | Topics |")
        w("|---|---|")
        for value, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            w(f"| {value} | {n} |")
        w("")
    w("**Topics that need each Kit kind** (a topic can need several, so this does not sum to 53)")
    w("")
    w("| Kind | Topics |")
    w("|---|---|")
    for value, n in sorted(c["kit kind needed (topics)"].items(), key=lambda kv: (-kv[1], kv[0])):
        w(f"| {value} | {n} |")
    w("")
    w("**Subject by model kind**")
    w("")
    w("| Subject | " + " | ".join(MODEL_KINDS) + " |")
    w("|---|" + "---|" * len(MODEL_KINDS))
    for subject in ("biology", "chemistry", "physics"):
        cnt = Counter(r["model_kind"] for r in rows if r["subject"] == subject)
        w(f"| {subject} | " + " | ".join(str(cnt.get(k, 0)) for k in MODEL_KINDS) + " |")
    w("")
    w("## 4. Science micro-models ordered by topics served")
    w("")
    w(
        "Proposed ids only. A model serving more topics earns its audit (citation, units, independent reference, properties, planted-bug suite) sooner."
    )
    w("")
    w("| Rank | Candidate model | Topics served | Which |")
    w("|---|---|---|---|")
    for rank, (model, slugs) in enumerate(model_ordering(rows), 1):
        w(f"| {rank} | `{model}` | {len(slugs)} | {', '.join(slugs)} |")
    w("")
    ordering = model_ordering(rows)
    shared = [(m, sl) for m, sl in ordering if len(sl) >= 2]
    w(
        f"{len(ordering)} distinct candidate models across the table. {len(shared)} of them serve more than one topic"
        + (": " + "; ".join(f"`{m}` ({', '.join(sl)})" for m, sl in shared) if shared else "")
        + ". Every other proposal serves exactly one topic, so this ordering is nearly flat and cannot by itself decide which models P1 builds first. "
        "The choice of a first vertical (section 5) is what orders them. Read the count as a number of proposals, not a forecast of Kit size (A-2)."
    )
    w("")
    w("## 5. Which first vertical the data supports")
    w("")
    w(
        "Scored per subject and per subject-and-form. `checkable` topics have a numeric or enumerable model, at least one candidate micro-model and a lane other than `free`. `strong` topics are checkable and annotated with high confidence."
    )
    w("")
    w("| Candidate vertical | Topics | Checkable | Strong | Distinct candidate models |")
    w("|---|---|---|---|---|")
    for sc in cluster_scores(rows):
        w(f"| {sc['name']} | {sc['topics']} | {sc['checkable']} | {sc['strong']} | {sc['models']} |")
    w("")
    w(render_ranking(rows))
    w("")
    w("## 6. Limits of this census")
    w("")
    w("- One annotator, no second reader, no inter-rater check. The owner's review is the only check.")
    w(
        "- Judged from topic names and short hints, never from the textbook. A topic's real content could change its row."
    )
    w("- `expected_lane` is a prediction of what verification an Environment will survive; nothing has been generated.")
    w(
        "- The candidate model ids are proposals. Whether each can be given an independent reference (A-5) is unmeasured."
    )
    w(
        "- Scene effort (drawing circuits, molecules, wave patterns) is not scored; it may dominate cost for the topics marked `high` here."
    )
    w(
        "- Chemistry placement in the taxonomy is lower confidence than Biology and Physics (see the source file's own note)."
    )
    w(
        "- `ui` and `pedagogy` are marked for every topic, so those two columns carry no information about which topics are hard."
    )
    w("")
    return "\n".join(lines)


def render_ranking(rows: list[dict]) -> str:
    scores = {c["name"]: c for c in cluster_scores(rows)}
    order = [c["name"] for c in cluster_scores(rows) if " form " not in c["name"]]
    lane = Counter(r["expected_lane"] for r in rows)
    kinds = counts(rows)["kit kind needed (topics)"]

    def cell(name: str) -> str:
        c = scores[name]
        return f"{c['strong']} strong and {c['checkable']} checkable of {c['topics']}"

    f5 = scores["physics form 5"]
    lines = [
        "**What the table says (an estimate).** By subject, in order of strong topics: "
        + "; ".join(f"{n} ({cell(n)})" for n in order)
        + ".",
        "",
        f"Physics leads: {cell('physics')}. Chemistry is second ({cell('chemistry')}). Biology is the largest subject but the weakest for a "
        f"verified, numbers-carrying Environment ({cell('biology')}): most of its topics are process or qualitative, so a science micro-model "
        "has little to own. A few Biology topics (`inheritance`, `movement_of_substances`, `dynamic_ecosystem`) are strong and are better "
        "picked up as individual wins than as the first vertical.",
        "",
        f"**Within Physics the table favours Form 4**: {cell('physics form 4')} against Form 5 with {cell('physics form 5')}. "
        "Form 4 is kinematics and momentum, circular motion and gravitation, heat, waves, and light and optics, all closed-form with textbook formulas.",
        "",
        "**A judgement the table does not score.** `mechanics.hookes` already exists in Kit v0 (Physics Form 5 `force_and_elasticity`), and "
        "`forces_and_pressure` and `electricity` are the simplest closed forms in the table with the least custom drawing. If Kit reuse "
        f"and low scene effort matter more than the count of strong topics, a Form 5 start ({f5['topics']} topics) is defensible. If the "
        "count of strong topics matters most, Form 4 is. The table cannot settle this; it is the owner's call, and D-09 stays open.",
        "",
        "**Two observations that may matter more than the ranking.**",
        "",
        f"- The scene library may be the long pole: {kinds['scene']} of 53 topics need `scene` parts (drawn apparatus, circuits, molecules, "
        f"waves) against {kinds['science']} that need a science micro-model. The census names {len(model_ordering(rows))} candidate science models "
        "for 53 topics, one or two per topic; how many a topic really needs cannot be told from its name, so this neither supports nor "
        "refutes the A-2 guess (about 120 scene, 150 to 250 science). It is a hypothesis that scene effort is under-weighted there.",
        f"- No row was predicted `free` (compose {lane['compose']}, instantiate {lane['instantiate']}, free {lane['free']}). That is more likely "
        "annotator optimism about what the Kit can express than a finding; the two `low`-confidence rows and every scene-heavy row are the "
        "likeliest to land in the Free lane when something is actually generated.",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    topics = load_topics()
    issues = problems(ROWS, topics)
    if "--check" in argv:
        if issues:
            print("census: FAILED")
            for p in issues:
                print("  -", p)
            return 1
        rows = joined(topics)
        c = counts(rows)
        sums_ok = all(
            sum(c[k].values()) == EXPECTED_ROWS
            for k in ("subject and form", "subject", "pattern", "model_kind", "expected_lane", "confidence")
        )
        if not sums_ok:
            print("census: FAILED (a count does not sum to 53)")
            return 1
        print(
            f"census: OK, {len(rows)} rows, unique slugs, every cell in its vocabulary, every count sums to {EXPECTED_ROWS}"
        )
        return 0
    if issues:
        print("census is invalid; run --check")
        return 1
    rows = joined(topics)
    if "--write-report" in argv:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(render_report(rows), encoding="utf-8")
        print(f"wrote {REPORT_FILE.relative_to(REPO)}")
        return 0
    if "--report" in argv:
        for name, counter in counts(rows).items():
            print(
                f"{name}: " + ", ".join(f"{k}={v}" for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))
            )
        print("\nscience micro-models by topics served:")
        for model, slugs in model_ordering(rows)[:15]:
            print(f"  {len(slugs)}  {model}: {', '.join(slugs)}")
        print("\nvertical scores (strong, checkable, topics):")
        for s in cluster_scores(rows):
            print(
                f"  {s['name']:<18} strong={s['strong']:<2} checkable={s['checkable']:<2} topics={s['topics']:<2} models={s['models']}"
            )
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
